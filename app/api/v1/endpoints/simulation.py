from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.database import get_db
from app.models import (
    Plan, User, UserSubscription, Greenhouse, Device, Sensor, SensorThreshold,
    TelemetryReading, Alert, AlertStatusEnum, AlertSeverityEnum,
    PlanTierEnum
)
from app.services.alert_engine import AlertEngine

router = APIRouter()

class UpdateReadingPayload(BaseModel):
    sensor_code: str = Field(..., description="Código del sensor (ej: TANK_1_PH, TANK_1_WATER_LEVEL, ENV_TEMP_AIR, GEN_FUEL, SOLAR_BATTERY_PCT)")
    value: float = Field(..., description="Nuevo valor numérico a registrar en la base de datos")
    tier: Optional[str] = Field("BASE", description="Nivel del plan del usuario (BASE, ESTANDAR, PREMIUM)")

class PresetPayload(BaseModel):
    preset: str = Field(..., description="Nombre del escenario preconfigurado: 'critico', 'optimo', 'alerta_temperatura', 'combustible_bajo', 'bateria_baja'")
    tier: Optional[str] = Field("BASE", description="Nivel del plan")

class ResolveAlertPayload(BaseModel):
    sensor_code: Optional[str] = Field(None, description="Código del sensor a normalizar")
    alert_id: Optional[str] = Field(None, description="ID UUID de la alerta a resolver")
    tier: Optional[str] = Field("BASE", description="Nivel del plan")


def get_primary_context(db: Session, tier: Optional[str] = None):
    """Obtiene el usuario, invernadero y dispositivo central unificado."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontraron usuarios en la BD.")

    if tier:
        plan_tier = PlanTierEnum(tier.upper()) if tier.upper() in [e.value for e in PlanTierEnum] else PlanTierEnum.BASE
        plan_obj = db.query(Plan).filter(Plan.tier == plan_tier).first()
        if plan_obj and user.subscription:
            user.subscription.plan_id = plan_obj.id
            db.commit()

    gh = db.query(Greenhouse).filter(Greenhouse.user_id == user.id, Greenhouse.is_active == True).first()
    if not gh:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró invernadero.")

    device = db.query(Device).filter(Device.greenhouse_id == gh.id, Device.is_active == True).first()
    return user, gh, device


@router.get("/state", summary="Obtener estado consolidado de la base de datos en tiempo real")
def get_simulation_state(tier: str = "BASE", db: Session = Depends(get_db)):
    """Retorna todas las lecturas actuales de la BD, rangos y alertas activas."""
    plan_tier = PlanTierEnum(tier.upper()) if tier.upper() in [e.value for e in PlanTierEnum] else PlanTierEnum.BASE
    user, gh, device = get_primary_context(db, tier)

    if not device:
        return {"sensors": {}, "alerts": [], "tier": plan_tier.value}

    # Sensores
    sensors = db.query(Sensor).filter(Sensor.device_id == device.id, Sensor.is_active == True).all()
    
    sensors_dict = {}
    for s in sensors:
        latest = db.query(TelemetryReading).filter(
            TelemetryReading.sensor_id == s.id
        ).order_by(TelemetryReading.recorded_at.desc(), TelemetryReading.id.desc()).first()

        cur_val = float(latest.value) if latest else None
        
        # Calcular status
        st = "NORMAL"
        t = s.threshold
        if cur_val is not None and t:
            min_c = float(t.min_critical_value) if t.min_critical_value is not None else None
            max_c = float(t.max_critical_value) if t.max_critical_value is not None else None
            min_s = float(t.min_safe_value) if t.min_safe_value is not None else None
            max_s = float(t.max_safe_value) if t.max_safe_value is not None else None

            if (min_c is not None and cur_val <= min_c) or (max_c is not None and cur_val >= max_c):
                st = "CRITICAL"
            elif (min_s is not None and cur_val < min_s) or (max_s is not None and cur_val > max_s):
                st = "WARNING"

        sensors_dict[s.sensor_code] = {
            "id": s.id,
            "sensor_code": s.sensor_code,
            "name": s.name,
            "unit": s.unit,
            "category": s.category.value if hasattr(s.category, 'value') else str(s.category),
            "current_value": cur_val,
            "status": st,
            "min_safe": float(t.min_safe_value) if t and t.min_safe_value is not None else None,
            "max_safe": float(t.max_safe_value) if t and t.max_safe_value is not None else None,
            "min_critical": float(t.min_critical_value) if t and t.min_critical_value is not None else None,
            "max_critical": float(t.max_critical_value) if t and t.max_critical_value is not None else None,
        }

    # Alertas activas
    active_alerts = db.query(Alert).filter(
        Alert.greenhouse_id == gh.id,
        Alert.status == AlertStatusEnum.ACTIVE
    ).order_by(Alert.created_at.desc()).all()

    alerts_list = []
    for a in active_alerts:
        sensor_code = a.sensor.sensor_code if a.sensor else None
        alerts_list.append({
            "id": a.id,
            "sensor_code": sensor_code,
            "title": a.title,
            "message": a.message,
            "pasos_resolucion": a.pasos_resolucion,
            "severity": a.severity.value,
            "status": a.status.value,
            "trigger_value": float(a.trigger_value) if a.trigger_value is not None else None,
            "threshold_value": float(a.threshold_value) if a.threshold_value is not None else None,
            "created_at": a.created_at.isoformat() if a.created_at else None
        })

    return {
        "user_email": user.email,
        "greenhouse_id": str(gh.id),
        "greenhouse_name": gh.name,
        "tier": plan_tier.value,
        "sensors": sensors_dict,
        "active_alerts": alerts_list,
        "active_alerts_count": len(alerts_list)
    }

@router.post("/update-reading", summary="Modificar un parámetro y registrar telemetría en PostgreSQL")
def update_reading(payload: UpdateReadingPayload, db: Session = Depends(get_db)):
    """
    Inserta una nueva lectura de telemetría en la BD y evalúa las alertas con el AlertEngine.
    """
    user, gh, device = get_primary_context(db, payload.tier)
    
    sensor = db.query(Sensor).filter(
        Sensor.device_id == device.id,
        Sensor.sensor_code == payload.sensor_code,
        Sensor.is_active == True
    ).first()

    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor '{payload.sensor_code}' no encontrado en el invernadero."
        )

    # 1. Insertar Telemetría en PostgreSQL
    reading = TelemetryReading(
        sensor_id=sensor.id,
        device_id=device.id,
        value=payload.value,
        recorded_at=datetime.now(timezone.utc)
    )
    db.add(reading)

    # 2. Evaluar Motor de Alertas
    alert = AlertEngine.evaluate_reading(
        db=db,
        sensor=sensor,
        greenhouse=gh,
        reading_value=payload.value
    )
    db.commit()

    # 3. Consultar Alertas Activas Totales
    total_active = db.query(Alert).filter(
        Alert.greenhouse_id == gh.id,
        Alert.status == AlertStatusEnum.ACTIVE
    ).count()

    return {
        "status": "success",
        "sensor_code": sensor.sensor_code,
        "new_value": payload.value,
        "unit": sensor.unit,
        "alert_triggered": {
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity.value
        } if alert else None,
        "total_active_alerts": total_active
    }

@router.post("/preset", summary="Aplicar preset de simulación completo en la base de datos")
def set_simulation_preset(payload: PresetPayload, db: Session = Depends(get_db)):
    """Aplica configuraciones rápidas de telemetría para pruebas."""
    user, gh, device = get_primary_context(db, payload.tier)

    readings_map = {}
    if payload.preset == "critico":
        readings_map = {
            "TANK_1_PH": 7.2,            # pH crítico (Safe: 5.5 - 6.5)
            "TANK_1_WATER_LEVEL": 25.0,  # Nivel crítico (Safe: > 35%)
            "ENV_TEMP_AIR": 32.5,        # Temp aire alta (Safe: 18 - 28)
        }
    elif payload.preset == "optimo":
        readings_map = {
            "TANK_1_PH": 6.2,
            "TANK_1_WATER_LEVEL": 85.0,
            "TANK_1_EC": 1.6,
            "TANK_1_TEMP_LIQUID": 21.0,
            "ENV_TEMP_AIR": 24.5,
            "ENV_HUMIDITY": 68.0,
            "GEN_FUEL": 78.0,
            "SOLAR_BATTERY_PCT": 92.0
        }
    elif payload.preset == "combustible_bajo":
        readings_map = {
            "GEN_FUEL": 12.0,            # Diésel crítico (Safe: > 35%)
            "GEN_BATTERY_VOLT": 11.6,
        }
    elif payload.preset == "bateria_baja":
        readings_map = {
            "SOLAR_BATTERY_PCT": 18.0,   # Batería solar crítica (Safe: > 40%)
            "SOLAR_POWER_WATTS": 800.0,
        }

    for code, val in readings_map.items():
        sensor = db.query(Sensor).filter(Sensor.device_id == device.id, Sensor.sensor_code == code).first()
        if sensor:
            db.add(TelemetryReading(sensor_id=sensor.id, device_id=device.id, value=val, recorded_at=datetime.now(timezone.utc)))
            AlertEngine.evaluate_reading(db=db, sensor=sensor, greenhouse=gh, reading_value=val)

    db.commit()

    total_active = db.query(Alert).filter(Alert.greenhouse_id == gh.id, Alert.status == AlertStatusEnum.ACTIVE).count()
    return {"status": "success", "preset_applied": payload.preset, "total_active_alerts": total_active}

@router.post("/resolve-alert", summary="Resolver alerta y restablecer parámetro individual en PostgreSQL")
def resolve_alert(payload: ResolveAlertPayload, db: Session = Depends(get_db)):
    """Marca ÚNICAMENTE la alerta seleccionada como RESUELTA en la base de datos y restablece su sensor a valores óptimos."""
    user, gh, device = get_primary_context(db, payload.tier)

    def get_optimal_value(code: str) -> float:
        if "PH" in code: return 6.2
        if "LEVEL" in code or "WATER" in code: return 85.0
        if "FUEL" in code: return 78.0
        if "SOLAR" in code or "BATTERY" in code: return 92.0
        if "TEMP" in code: return 22.0
        if "CO2" in code: return 720.0
        if "FLOW" in code: return 14.0
        return 50.0

    target_sensors = set()
    resolved_count = 0

    # 1. Resolución por ID de Alerta
    if payload.alert_id:
        try:
            import uuid
            alert_uuid = uuid.UUID(str(payload.alert_id))
            alert = db.query(Alert).filter(Alert.id == alert_uuid).first()
        except Exception:
            alert = db.query(Alert).filter(Alert.id == payload.alert_id).first()

        if alert:
            alert.status = AlertStatusEnum.RESOLVED
            alert.resolved_at = datetime.now(timezone.utc)
            db.add(alert)
            resolved_count += 1
            if alert.sensor:
                target_sensors.add(alert.sensor)

    # 2. Resolución por Código de Sensor
    if payload.sensor_code:
        sensor = db.query(Sensor).filter(Sensor.device_id == device.id, Sensor.sensor_code == payload.sensor_code).first()
        if sensor:
            active_alerts = db.query(Alert).filter(Alert.sensor_id == sensor.id, Alert.status == AlertStatusEnum.ACTIVE).all()
            for a in active_alerts:
                if a.status != AlertStatusEnum.RESOLVED:
                    a.status = AlertStatusEnum.RESOLVED
                    a.resolved_at = datetime.now(timezone.utc)
                    db.add(a)
                    resolved_count += 1
            target_sensors.add(sensor)

    # 3. Si no se especificó nada, resolver todas las alertas activas
    if not payload.alert_id and not payload.sensor_code:
        active_alerts = db.query(Alert).filter(Alert.greenhouse_id == gh.id, Alert.status == AlertStatusEnum.ACTIVE).all()
        for a in active_alerts:
            a.status = AlertStatusEnum.RESOLVED
            a.resolved_at = datetime.now(timezone.utc)
            db.add(a)
            resolved_count += 1
            if a.sensor:
                target_sensors.add(a.sensor)

    # Registrar nuevas lecturas óptimas en PostgreSQL para los sensores normalizados
    for s in target_sensors:
        opt_val = get_optimal_value(s.sensor_code)
        db.add(TelemetryReading(
            sensor_id=s.id,
            device_id=device.id,
            value=opt_val,
            recorded_at=datetime.now(timezone.utc)
        ))

    db.commit()

    total_active = db.query(Alert).filter(Alert.greenhouse_id == gh.id, Alert.status == AlertStatusEnum.ACTIVE).count()
    return {
        "status": "resolved",
        "resolved_alerts_count": resolved_count,
        "message": f"{resolved_count} alerta(s) resuelta(s) y parámetro restablecido en PostgreSQL.",
        "total_active_alerts": total_active
    }

