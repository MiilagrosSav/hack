import logging
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.models import (
    Sensor, SensorThreshold, Alert, Greenhouse,
    AlertSeverityEnum, AlertStatusEnum
)

logger = logging.getLogger(__name__)

class AlertEngine:
    """
    Motor de Alertas Tempranas para Invernaderos Hidropónicos.
    Evalúa lecturas de telemetría en tiempo real contra umbrales seguros y críticos.
    """

    @staticmethod
    def evaluate_reading(
        db: Session,
        sensor: Sensor,
        greenhouse: Greenhouse,
        reading_value: float
    ) -> Optional[Alert]:
        """
        Evalúa una lectura individual contra los umbrales del sensor.
        Si se detecta una anomalía, crea o actualiza una alerta en la BD.
        """
        threshold: Optional[SensorThreshold] = sensor.threshold
        if not threshold or not threshold.is_enabled:
            return None

        val = float(reading_value)
        severity: Optional[AlertSeverityEnum] = None
        message: Optional[str] = None
        threshold_val: Optional[float] = None

        # 1. Evaluación de Umbrales Críticos (Prioridad Alta)
        if threshold.min_critical_value is not None and val <= float(threshold.min_critical_value):
            severity = AlertSeverityEnum.CRITICAL
            threshold_val = float(threshold.min_critical_value)
            message = threshold.critical_message or f"¡PELIGRO CRÍTICO! {sensor.name} ha caído a {val} {sensor.unit} (Mínimo crítico: {threshold_val} {sensor.unit})."

        elif threshold.max_critical_value is not None and val >= float(threshold.max_critical_value):
            severity = AlertSeverityEnum.CRITICAL
            threshold_val = float(threshold.max_critical_value)
            message = threshold.critical_message or f"¡PELIGRO CRÍTICO! {sensor.name} ha subido a {val} {sensor.unit} (Máximo crítico: {threshold_val} {sensor.unit})."

        # 2. Evaluación de Umbrales de Advertencia (Warning)
        elif threshold.min_safe_value is not None and val < float(threshold.min_safe_value):
            severity = AlertSeverityEnum.WARNING
            threshold_val = float(threshold.min_safe_value)
            message = threshold.warning_message or f"Advertencia: {sensor.name} bajo ({val} {sensor.unit}). Rango seguro mínimo: {threshold_val} {sensor.unit}."

        elif threshold.max_safe_value is not None and val > float(threshold.max_safe_value):
            severity = AlertSeverityEnum.WARNING
            threshold_val = float(threshold.max_safe_value)
            message = threshold.warning_message or f"Advertencia: {sensor.name} alto ({val} {sensor.unit}). Rango seguro máximo: {threshold_val} {sensor.unit}."

        # Si el valor está dentro de los rangos seguros, resolvemos alertas activas previas
        if severity is None:
            active_alert = db.query(Alert).filter(
                Alert.sensor_id == sensor.id,
                Alert.greenhouse_id == greenhouse.id,
                Alert.status == AlertStatusEnum.ACTIVE
            ).first()
            if active_alert:
                active_alert.status = AlertStatusEnum.RESOLVED
                active_alert.resolved_at = datetime.utcnow()
                db.add(active_alert)
                logger.info(f"Alerta resuelta automáticamente para {sensor.name} en Invernadero {greenhouse.name}")
            return None

        # Si hay una anomalía detectada, verificamos si ya existe una alerta activa para evitar saturación (spam)
        existing_alert = db.query(Alert).filter(
            Alert.sensor_id == sensor.id,
            Alert.greenhouse_id == greenhouse.id,
            Alert.status == AlertStatusEnum.ACTIVE,
            Alert.severity == severity
        ).first()

        if existing_alert:
            # Actualizamos el valor disparador reciente
            existing_alert.trigger_value = val
            db.add(existing_alert)
            return existing_alert

        # Creamos una nueva alerta activa
        new_alert = Alert(
            greenhouse_id=greenhouse.id,
            sensor_id=sensor.id,
            severity=severity,
            status=AlertStatusEnum.ACTIVE,
            title=f"Alerta en {sensor.name}",
            message=message,
            trigger_value=val,
            threshold_value=threshold_val,
            created_at=datetime.utcnow()
        )
        db.add(new_alert)
        logger.warning(f"[ALERTA GENERADA] [{severity.value}] {new_alert.title}: {new_alert.message}")
        return new_alert
