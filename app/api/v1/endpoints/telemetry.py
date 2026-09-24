from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password
from app.models import Device, Sensor, TelemetryReading, Greenhouse
from app.schemas.telemetry import TelemetryIngestPayload, TelemetryIngestResponse
from app.services.alert_engine import AlertEngine
import hashlib

router = APIRouter()

def hash_api_key(raw_key: str) -> str:
    """Función de hashing rápido para claves de API de microcontroladores."""
    return hashlib.sha256(raw_key.encode()).hexdigest()

@router.post(
    "/ingest",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingesta de Telemetría IoT desde Microcontroladores",
    description="Endpoint seguro para que los dispositivos (ESP32 / Raspberry Pi / Gateways) envíen sus lecturas de sensores en lote."
)
def ingest_telemetry(payload: TelemetryIngestPayload, db: Session = Depends(get_db)):
    # 1. Validar autenticación del dispositivo mediante device_uid y API Key
    device = db.query(Device).filter(Device.device_uid == payload.device_uid, Device.is_active == True).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Dispositivo IoT no registrado o inactivo."
        )

    # Validar API key (comparamos con el hash almacenado)
    provided_hash = hash_api_key(payload.api_key)
    if device.api_key_hash != provided_hash and device.api_key_hash != payload.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Credenciales de dispositivo inválidas (API Key incorrecta)."
        )

    greenhouse = device.greenhouse
    if not greenhouse or not greenhouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El invernadero asociado a este dispositivo se encuentra inactivo."
        )

    # 2. Actualizar último heartbeat del dispositivo
    device.last_heartbeat = payload.timestamp
    db.add(device)

    # 3. Cachear mapa de sensores existentes para este dispositivo
    sensors = db.query(Sensor).filter(Sensor.device_id == device.id, Sensor.is_active == True).all()
    sensor_map = {s.sensor_code: s for s in sensors}

    processed_count = 0
    triggered_alerts_count = 0

    # 4. Procesar lecturas, almacenar en series de tiempo y evaluar alertas
    for item in payload.readings:
        sensor = sensor_map.get(item.sensor_code)
        if not sensor:
            # Si el sensor no existe para este dispositivo, lo ignoramos o creamos según política
            continue

        # Crear registro de telemetría
        reading_entry = TelemetryReading(
            sensor_id=sensor.id,
            device_id=device.id,
            recorded_at=payload.timestamp,
            value=item.value,
            raw_payload=payload.metadata
        )
        db.add(reading_entry)
        processed_count += 1

        # Ejecutar Motor de Alertas Tempranas
        alert = AlertEngine.evaluate_reading(
            db=db,
            sensor=sensor,
            greenhouse=greenhouse,
            reading_value=item.value
        )
        if alert:
            triggered_alerts_count += 1

    # Confirmar transacción en PostgreSQL
    db.commit()

    return TelemetryIngestResponse(
        status="success",
        processed_readings=processed_count,
        triggered_alerts=triggered_alerts_count
    )
