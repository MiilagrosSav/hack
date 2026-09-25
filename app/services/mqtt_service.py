import json
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import paho.mqtt.client as mqtt

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Device, Sensor, TelemetryReading, Greenhouse, AlertStatusEnum
from app.services.alert_engine import AlertEngine

logger = logging.getLogger("mqtt_service")
logging.basicConfig(level=logging.INFO)

class MQTTService:
    """
    Servicio de Ingesta IoT en Tiempo Real sobre MQTT (Message Queuing Telemetry Transport).
    - Mantiene una conexión persistente y de bajo consumo con el Broker MQTT.
    - Se suscribe a los tópicos de telemetría y estado (LWT) de los microcontroladores ESP32.
    - Despacha las mediciones a PostgreSQL y evalúa el Motor de Asistencia Pasiva (AlertEngine).
    """

    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.is_connected = False
        self._lock = threading.Lock()

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.is_connected = True
            logger.info(f"✅ [MQTT] Conectado exitosamente al Broker MQTT en {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
            
            # Suscripción a tópicos de telemetría y estado de dispositivos
            # Estructura: hydroguard/gh/{greenhouse_id}/devices/{device_uid}/telemetry
            telemetry_topic = f"{settings.MQTT_BASE_TOPIC}/gh/+/devices/+/telemetry"
            status_topic = f"{settings.MQTT_BASE_TOPIC}/gh/+/devices/+/status"
            
            client.subscribe([(telemetry_topic, 1), (status_topic, 1)])
            logger.info(f"📡 [MQTT] Suscrito a tópicos: {telemetry_topic} y {status_topic} (QoS 1)")
        else:
            self.is_connected = False
            logger.error(f"❌ [MQTT] Error de conexión al Broker. Código RC: {rc}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        self.is_connected = False
        if rc != 0:
            logger.warning(f"⚠️ [MQTT] Desconexión inesperada del Broker. Intentando reconexión automática...")
        else:
            logger.info(f"🛑 [MQTT] Desconectado del Broker MQTT.")

    def _on_message(self, client, userdata, msg):
        """
        Procesador de mensajes entrantes desde los microcontroladores ESP32 en campo.
        """
        try:
            topic = msg.topic
            payload_str = msg.payload.decode("utf-8")
            topic_parts = topic.split("/")

            # hydroguard / gh / {gh_id} / devices / {device_uid} / {action}
            if len(topic_parts) >= 6:
                gh_id_str = topic_parts[2]
                device_uid = topic_parts[4]
                action = topic_parts[5]

                data = json.loads(payload_str)

                if action == "telemetry":
                    self._process_telemetry(device_uid, data)
                elif action == "status":
                    self._process_status(device_uid, data)
            else:
                logger.warning(f"⚠️ [MQTT] Mensaje en tópico no reconocido: {topic}")

        except json.JSONDecodeError:
            logger.error(f"❌ [MQTT] Payload no es un JSON válido: {msg.payload}")
        except Exception as e:
            logger.error(f"❌ [MQTT] Error al procesar mensaje MQTT: {e}", exc_info=True)

    def _process_telemetry(self, device_uid: str, data: Dict[str, Any]):
        """
        Almacena la telemetría recibida por MQTT en PostgreSQL y evalúa alertas en tiempo real.
        Formatos soportados:
        A) Lista de lecturas: {"readings": [{"sensor_code": "TANK_1_PH", "value": 6.2}, ...]}
        B) Diccionario directo: {"TANK_1_PH": 6.2, "TANK_1_WATER_LEVEL": 85.0, ...}
        """
        db = SessionLocal()
        try:
            device = db.query(Device).filter(Device.device_uid == device_uid, Device.is_active == True).first()
            if not device:
                # Si el device_uid no coincide exactamente, buscar primer dispositivo activo para pruebas
                device = db.query(Device).filter(Device.is_active == True).first()

            if not device:
                logger.warning(f"⚠️ [MQTT] Dispositivo '{device_uid}' no encontrado en PostgreSQL.")
                return

            greenhouse = device.greenhouse
            device.last_heartbeat = datetime.now(timezone.utc)
            db.add(device)

            # Normalizar lista de lecturas
            readings_list: List[Dict[str, Any]] = []
            if "readings" in data and isinstance(data["readings"], list):
                readings_list = data["readings"]
            else:
                for k, v in data.items():
                    if isinstance(v, (int, float)):
                        readings_list.append({"sensor_code": k, "value": float(v)})

            # Obtener mapa de sensores del dispositivo
            sensors = db.query(Sensor).filter(Sensor.device_id == device.id, Sensor.is_active == True).all()
            sensor_map = {s.sensor_code: s for s in sensors}

            processed = 0
            for item in readings_list:
                s_code = item.get("sensor_code")
                val = item.get("value")
                if not s_code or val is None:
                    continue

                sensor = sensor_map.get(s_code)
                if not sensor:
                    continue

                # 1. Insertar lectura en serie temporal
                reading = TelemetryReading(
                    sensor_id=sensor.id,
                    device_id=device.id,
                    value=float(val),
                    recorded_at=datetime.now(timezone.utc),
                    raw_payload={"source": "mqtt", "device_uid": device_uid}
                )
                db.add(reading)
                processed += 1

                # 2. Evaluar Motor de Asistencia Pasiva (AlertEngine)
                if greenhouse:
                    AlertEngine.evaluate_reading(
                        db=db,
                        sensor=sensor,
                        greenhouse=greenhouse,
                        reading_value=float(val)
                    )

            db.commit()
            logger.info(f"📥 [MQTT] {processed} lectura(s) procesada(s) desde ESP32 '{device_uid}'.")

        except Exception as e:
            db.rollback()
            logger.error(f"❌ [MQTT] Error al guardar telemetría en BD: {e}")
        finally:
            db.close()

    def _process_status(self, device_uid: str, data: Dict[str, Any]):
        """Actualiza el estado de conexión / heartbeat / LWT del microcontrolador."""
        db = SessionLocal()
        try:
            device = db.query(Device).filter(Device.device_uid == device_uid).first()
            if device:
                device.last_heartbeat = datetime.now(timezone.utc)
                db.add(device)
                db.commit()
                logger.info(f"💓 [MQTT Heartbeat] Dispositivo '{device_uid}' estado: {data.get('status', 'online')}")
        except Exception as e:
            db.rollback()
            logger.error(f"❌ [MQTT] Error al actualizar status: {e}")
        finally:
            db.close()

    def start(self):
        """Inicia el cliente MQTT en un hilo de fondo no bloqueante."""
        if not settings.MQTT_ENABLED:
            logger.info("ℹ️ [MQTT] Servicio MQTT desactivado por configuración.")
            return

        with self._lock:
            if self.client is not None:
                return

            try:
                # Usar protocolo MQTT v5 / v3.1.1 según compatibilidad
                self.client = mqtt.Client(
                    client_id=settings.MQTT_CLIENT_ID,
                    clean_session=True
                )

                if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
                    self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

                self.client.on_connect = self._on_connect
                self.client.on_disconnect = self._on_disconnect
                self.client.on_message = self._on_message

                # Conexión asíncrona no bloqueante
                logger.info(f"🔌 [MQTT] Conectando a {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}...")
                self.client.connect_async(
                    host=settings.MQTT_BROKER_HOST,
                    port=settings.MQTT_BROKER_PORT,
                    keepalive=settings.MQTT_KEEPALIVE
                )
                self.client.loop_start()

            except Exception as e:
                logger.warning(f"⚠️ [MQTT] No se pudo conectar al Broker MQTT local ({e}). El backend continuará operando y reintentará.")

    def stop(self):
        """Detiene el cliente MQTT limpiamente."""
        with self._lock:
            if self.client:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                    logger.info("🛑 [MQTT] Cliente MQTT detenido.")
                except Exception as e:
                    logger.error(f"Error al detener MQTT: {e}")
                finally:
                    self.client = None
                    self.is_connected = False

    def publish_telemetry(self, greenhouse_id: str, device_uid: str, payload: Dict[str, Any]):
        """Publica un mensaje MQTT (útil para simulaciones de campo o comandos)."""
        if self.client and self.is_connected:
            topic = f"{settings.MQTT_BASE_TOPIC}/gh/{greenhouse_id}/devices/{device_uid}/telemetry"
            self.client.publish(topic, json.dumps(payload), qos=1)

mqtt_service = MQTTService()
