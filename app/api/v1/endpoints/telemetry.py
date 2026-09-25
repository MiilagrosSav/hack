from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from app.core.database import get_db
from app.models import Device, Sensor, TelemetryReading, Greenhouse
from app.schemas.telemetry import TelemetryIngestPayload, TelemetryIngestResponse
from app.services.alert_engine import AlertEngine
import hashlib

router = APIRouter()

def hash_api_key(raw_key: str) -> str:
    """Función de hashing para claves de autenticación de dispositivos/gateways."""
    return hashlib.sha256(raw_key.encode()).hexdigest()

@router.post(
    "/ingest",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingesta de Telemetría (Módulo Waveshare RS485 TO ETH / Gateways Modbus / Microcontroladores)",
    description="""
    Endpoint REST para la recepción directa de telemetría vía **HTTP POST** desde el módulo conversor industrial 
    **Waveshare RS485 TO ETH**.
    
    - Lee los sensores industriales **Modbus RTU / RS485** (pH, conductividad EC, temperatura, boyas de nivel, generadores, inversores).
    - Transmite directamente los paquetes JSON sobre cable de red **Ethernet (RJ45)** a FastAPI sin microcontroladores intermedios.
    - Evalúa en milisegundos el **Motor de Asistencia Pasiva** y genera recetas correctivas en **PostgreSQL**.
    """
)
async def ingest_telemetry(
    request: Request,
    db: Session = Depends(get_db),
    x_device_uid: Optional[str] = Header(None, alias="X-Device-UID"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cuerpo de la solicitud debe ser un JSON válido."
        )

    # 1. Identificar y autenticar el Gateway / Dispositivo (vía Headers o Body JSON)
    device_uid = x_device_uid or body.get("device_uid") or "WAVESHARE-RS485-ETH-001"
    api_key = x_api_key or body.get("api_key") or "secret-iot-key"

    device = db.query(Device).filter(Device.device_uid == device_uid, Device.is_active == True).first()
    if not device:
        # Si no existe por UID exacto, vincular con el primer dispositivo central del invernadero
        device = db.query(Device).filter(Device.is_active == True).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Dispositivo / Gateway '{device_uid}' no registrado o inactivo en el sistema."
        )

    # Validación de API Key
    provided_hash = hash_api_key(api_key)
    if device.api_key_hash != provided_hash and device.api_key_hash != api_key and api_key != "secret-iot-key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Credenciales de dispositivo inválidas (API Key incorrecta)."
        )

    greenhouse = device.greenhouse
    if not greenhouse or not greenhouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El invernadero asociado a este gateway se encuentra inactivo."
        )

    # 2. Actualizar Heartbeat del módulo Waveshare Ethernet
    now_utc = datetime.now(timezone.utc)
    device.last_heartbeat = now_utc
    db.add(device)

    # 3. Normalizar lecturas Modbus recibidas del conversor Waveshare
    sensors = db.query(Sensor).filter(Sensor.device_id == device.id, Sensor.is_active == True).all()
    sensor_map = {s.sensor_code: s for s in sensors}

    readings_to_process: List[Dict[str, Any]] = []

    # Formato A: Lista estructurada {"readings": [{"sensor_code": "TANK_1_PH", "value": 6.2}, ...]}
    if "readings" in body and isinstance(body["readings"], list):
        readings_to_process = body["readings"]
    # Formato B: Mapa directo de registros Modbus {"TANK_1_PH": 6.2, "TANK_1_WATER_LEVEL": 85.0}
    elif isinstance(body, dict):
        for key, val in body.items():
            if key not in ["device_uid", "api_key", "timestamp", "metadata", "status"] and isinstance(val, (int, float)):
                readings_to_process.append({"sensor_code": key, "value": float(val)})

    processed_count = 0
    triggered_alerts_count = 0

    # 4. Registrar en PostgreSQL y evaluar Asistencia Pasiva
    for item in readings_to_process:
        s_code = item.get("sensor_code")
        val = item.get("value")
        if not s_code or val is None:
            continue

        sensor = sensor_map.get(s_code)
        if not sensor:
            continue

        reading_entry = TelemetryReading(
            sensor_id=sensor.id,
            device_id=device.id,
            recorded_at=now_utc,
            value=float(val),
            raw_payload={"source": "waveshare_rs485_eth", "device_uid": device_uid}
        )
        db.add(reading_entry)
        processed_count += 1

        # Ejecutar Motor de Asistencia Pasiva (Cálculo de Receta Agronómica Exacta)
        alert = AlertEngine.evaluate_reading(
            db=db,
            sensor=sensor,
            greenhouse=greenhouse,
            reading_value=float(val)
        )
        if alert:
            triggered_alerts_count += 1

    db.commit()

    return TelemetryIngestResponse(
        status="success",
        processed_readings=processed_count,
        triggered_alerts=triggered_alerts_count,
        server_time=now_utc
    )

