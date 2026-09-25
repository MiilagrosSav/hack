import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models import (
    Sensor, SensorThreshold, Alert, Greenhouse, Tank,
    AlertSeverityEnum, AlertStatusEnum
)

logger = logging.getLogger(__name__)

class AlertEngine:
    """
    Motor de Asistencia Pasiva y Alertas Tempranas para Invernaderos Hidropónicos.
    - Evalúa lecturas en tiempo real contra umbrales configurados.
    - NO ejecuta acciones físicas ni motores (cumpliendo rol de monitoreo pasivo).
    - Calcula mediante fórmulas agronómicas/operacionales la corrección exacta (Recetario Paso a Paso).
    """

    @staticmethod
    def calculate_resolution_recipe(sensor: Sensor, val: float, severity: AlertSeverityEnum) -> str:
        """
        Fórmula de Corrección Exacta: Genera dinámicamente los pasos de resolución
        indicando la dosis precisa de reactivo químico, litros o maniobra física manual requerida.
        """
        code = sensor.sensor_code
        tank_cap = 1000.0
        tank_name = "Tanque Principal"
        if sensor.tank:
            tank_cap = float(sensor.tank.capacity_liters) if sensor.tank.capacity_liters else 1000.0
            tank_name = sensor.tank.name

        # ---------------------------------------------------------------------
        # 1. pH DEL AGUA / SOLUCIÓN NUTRITIVA (Corrección con Buffer pH+ o pH-)
        # ---------------------------------------------------------------------
        if "PH" in code:
            if val < 5.5:
                # pH Ácido -> Requiere Incrementador pH+ (KOH / Carbonato de Potasio)
                delta_ph = max(0.1, 6.0 - val)
                # Dosis estándar: ~20 ml de solución correctora pH+ al 10% por cada 100L por cada 1.0 punto de pH
                ml_dose = round((tank_cap / 100.0) * delta_ph * 20.0, 1)
                return (
                    f"Receta Correctiva: pH Ácido ({val:.1f} pH) en {tank_name}\n\n"
                    f"• Dosis calculada: {ml_dose} ml de Solución Buffer Incrementadora (pH Up / KOH al 10%).\n"
                    f"• Paso 1: Medir exactamente {ml_dose} ml de solución correctora en probeta plástica limpia.\n"
                    f"• Paso 2: Diluir los {ml_dose} ml en un balde con 5 Litros de agua del mismo tanque (nunca verter puro).\n"
                    f"• Paso 3: Verter la mezcla lentamente en la zona de mayor agitación/retorno del {tank_name} ({tank_cap:.0f} L).\n"
                    f"• Paso 4: Dejar recircular la solución durante 30 minutos y el sistema revisará que se haya estabilizado."
                )
            elif val > 6.5:
                # pH Alcalino -> Requiere Reductor pH- (Ácido Fosfórico / Nítrico al 10%)
                delta_ph = max(0.1, val - 6.0)
                ml_dose = round((tank_cap / 100.0) * delta_ph * 24.0, 1)
                return (
                    f"Receta Correctiva: pH Alcalino ({val:.1f} pH) en {tank_name}\n\n"
                    f"• Dosis calculada: {ml_dose} ml de Solución Reductora (pH Down / Ácido Fosfórico al 10%).\n"
                    f"• Paso 1: Equiparse con guantes de nitrilo y antiparras protectoras.\n"
                    f"• Paso 2: Medir {ml_dose} ml de corrector pH- y diluirlos en 5 Litros de agua en balde.\n"
                    f"• Paso 3: Incorporar la dilución al {tank_name} ({tank_cap:.0f} L) con la bomba de recirculación activa.\n"
                    f"• Paso 4: Esperar 30 minutos de homogeneización el sistema verificará que se haya estabilizado."
                )

        # ---------------------------------------------------------------------
        # 2. NIVEL DE AGUA EN TANQUE (Reposición y Compensación de Volumen)
        # ---------------------------------------------------------------------
        if "LEVEL" in code or "WATER" in code:
            if val < 35.0:
                missing_pct = max(5.0, 85.0 - val)
                liters_needed = round((missing_pct / 100.0) * tank_cap, 0)
                return (
                    f"Receta Correctiva: Nivel Crítico ({val:.0f}%) en {tank_name}\n\n"
                    f"• Reposición estimada: {liters_needed:.0f} Litros de agua limpia/desclorada.\n"
                    f"• Paso 1: Abrir la válvula manual de carga de agua de red o pozo tratada.\n"
                    f"• Paso 2: Llenar el {tank_name} ({tank_cap:.0f} L) hasta alcanzar el nivel seguro (85% de capacidad).\n"
                    f"• Paso 3: Cerrar la válvula y revisar visualmente que no existan pérdidas en racores ni flotante trabado.\n"
                )

        # ---------------------------------------------------------------------
        # 3. CONDUCTIVIDAD ELÉCTRICA / NUTRIENTES EC (Fertirriego NFT)
        # ---------------------------------------------------------------------
        if "EC" in code:
            if val < 1.2:
                # Falta de sales nutritivas
                delta_ec = max(0.1, 1.6 - val)
                dose_part = round((tank_cap / 1000.0) * delta_ec * 350.0, 0)
                return (
                    f"Receta Correctiva: Nutrientes Bajos ({val:.2f} mS/cm) en {tank_name}\n\n"
                    f"• Dosis calculada: {dose_part:.0f} ml de Solución A + {dose_part:.0f} ml de Solución B.\n"
                    f"• Paso 1: Dosificar {dose_part:.0f} ml de Concentrado A (Calcio/Nitrato) en jarra graduada.\n"
                    f"• Paso 2: Dosificar {dose_part:.0f} ml de Concentrado B (Fósforo/Micros) en jarra separada.\n"
                    f"• Paso 3: Verter la Parte A en el {tank_name}, recircular 5 minutos y luego añadir la Parte B (nunca mezclar puras).\n"
                    f"• Paso 4: Dejar recircular 20 minutos y el sistema verificará que se haya estabilizado."
                )
            elif val > 2.0:
                # Exceso de sales / Riesgo de fitotoxicidad
                water_to_dilute = round(tank_cap * ((val - 1.6) / val), 0)
                return (
                    f"Receta Correctiva: Exceso de Salinidad ({val:.2f} mS/cm) en {tank_name}\n\n"
                    f"• Dilución requerida: {water_to_dilute:.0f} Litros de agua pura sin nutrientes.\n"
                    f"• Paso 1: Agregar {water_to_dilute:.0f} Litros de agua fresca al {tank_name} para diluir la solución madre.\n"
                    f"• Paso 2: Recircular el sistema por 15 minutos.\n"
                    f"• Paso 3: El sistema verificará que se haya estabilizado."
                )

        # ---------------------------------------------------------------------
        # 4. TEMPERATURA DEL LÍQUIDO DEL TANQUE
        # ---------------------------------------------------------------------
        if "TEMP_LIQUID" in code:
            if val > 24.0:
                return (
                    f"Receta Correctiva: Temperatura Alta en Solución ({val:.1f} °C)\n\n"
                    f"• Paso 1: Sombrear el depósito {tank_name} con aislante térmico o media sombra aluminizada.\n"
                    f"• Paso 2: Aumentar la aireación con difusor de oxígeno (a mayor temperatura, menor solubilidad de O₂).\n"
                    f"• Paso 3: Programar los riegos de mayor caudal en horarios nocturnos o matutinos más frescos."
                )
            elif val < 18.0:
                return (
                    f"Receta Correctiva: Temperatura Fría en Solución ({val:.1f} °C)\n\n"
                    f"• Paso 1: Inspeccionar la resistencia sumergible/termostato del {tank_name}.\n"
                    f"• Paso 2: Evitar ingresos masivos de agua helada directa de pozo en horas de la madrugada."
                )

        # ---------------------------------------------------------------------
        # 5. MICROCLIMA INVERNADERO (Temperatura y Humedad del Aire)
        # ---------------------------------------------------------------------
        if "ENV_TEMP_AIR" in code:
            if val > 28.0:
                return (
                    f"Receta Correctiva: Golpe de Calor en Invernadero ({val:.1f} °C)\n\n"
                    f"• Paso 1: Desplegar manualmente la malla semisombra al 65% sobre la nave del invernadero.\n"
                    f"• Paso 2: Abrir al 100% las ventanas cenitales superiores y cortinas laterales para generar tiro térmico.\n"
                    f"• Paso 3: Humedecer los pasillos de tránsito durante 3 minutos para refrigeración evaporativa pasiva."
                )
            elif val < 18.0:
                return (
                    f"Receta Correctiva: Descenso Térmico en Invernadero ({val:.1f} °C)\n\n"
                    f"• Paso 1: Cerrar herméticamente cortinas perimetrales y cenitales antes del atardecer.\n"
                    f"• Paso 2: Encender el calefactor pasivo/generador de aire tibio para evitar heladas sobre el follaje."
                )

        if "ENV_HUMIDITY" in code:
            if val > 80.0:
                return (
                    f"Receta Correctiva: Humedad Excesiva ({val:.0f}%)\n\n"
                    f"• Paso 1: Abrir ventilaciones laterales para facilitar circulación de aire seco y prevenir Botrytis/hongos.\n"
                    f"• Paso 2: Evitar cualquier mojado de hojas o pulverizaciones durante este período."
                )
            elif val < 55.0:
                return (
                    f"Receta Correctiva: Ambiente Seco ({val:.0f}%)\n\n"
                    f"• Paso 1: Humedecer los pasillos o activar nebulizadores 2 minutos para elevar la humedad ambiente.\n"
                    f"• Paso 2: Regular la apertura de cortinas contra el viento seco dominante."
                )

        # ---------------------------------------------------------------------
        # 6. GENERADOR ELÉCTRICO & COMBUSTIBLE
        # ---------------------------------------------------------------------
        if "GEN_FUEL" in code:
            liters_fuel = max(10.0, round(100.0 - val, 0))
            return (
                f"Receta Correctiva: Nivel Crítico de Diésel ({val:.0f}%)\n\n"
                f"• Carga requerida: ~{liters_fuel:.0f} Litros de combustible Diésel Grado 2/Euro.\n"
                f"• Paso 1: Girar la llave selectora del generador a posición OFF/SEGURO antes de cargar.\n"
                f"• Paso 2: Cargar {liters_fuel:.0f} Litros de combustible limpio con embudo con filtro trampa de agua.\n"
                f"• Paso 3: Ajustar la tapa hermética y devolver la llave a modo AUTOMÁTICO (En espera de emergencia)."
            )

        # ---------------------------------------------------------------------
        # 7. BANCO DE BATERÍAS & ENERGÍA SOLAR
        # ---------------------------------------------------------------------
        if "SOLAR_BATTERY" in code:
            return (
                f"Receta Correctiva: Batería Solar en Reserva ({val:.0f}%)\n\n"
                f"• Paso 1: Apagar cargas secundarias no esenciales (iluminación perimetral, bombas accesorias).\n"
                f"• Paso 2: Inspeccionar los paneles fotovoltaicos en cubierta y remover polvo o suciedad acumulada.\n"
                f"• Paso 3: Preparar la transferencia manual al generador en caso de pronóstico nublado continuo."
            )

        # Genérico para cualquier otro parámetro
        return (
            f"Receta Correctiva: Sensor {sensor.name} fuera de rango ({val} {sensor.unit})\n\n"
            f"• Paso 1: Inspeccionar físicamente el sensor y verificar que no tenga suciedad o incrustaciones.\n"
            f"• Paso 2: Realizar una contramedición manual con equipo portátil para confirmar la lectura.\n"
            f"• Paso 3: Ajustar manualmente los controles del subsistema y monitorear evolución durante 30 minutos."
        )

    @staticmethod
    def evaluate_reading(
        db: Session,
        sensor: Sensor,
        greenhouse: Greenhouse,
        reading_value: float
    ) -> Optional[Alert]:
        """
        Evalúa una lectura individual contra los umbrales del sensor.
        Si se detecta una anomalía, genera o actualiza la alerta incorporando
        la receta de resolución exacta calculada.
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
            active_alerts = db.query(Alert).filter(
                Alert.sensor_id == sensor.id,
                Alert.greenhouse_id == greenhouse.id,
                Alert.status == AlertStatusEnum.ACTIVE
            ).all()
            for active_alert in active_alerts:
                active_alert.status = AlertStatusEnum.RESOLVED
                active_alert.resolved_at = datetime.now(timezone.utc)
                db.add(active_alert)
                logger.info(f"Alerta resuelta automáticamente para {sensor.name} en Invernadero {greenhouse.name}")
            return None

        # Calcular receta de resolución exacta con el Motor de Asistencia Pasiva
        resolution_recipe = AlertEngine.calculate_resolution_recipe(sensor, val, severity)

        # Si hay una anomalía detectada, verificamos si ya existe una alerta activa para evitar duplicados
        existing_alert = db.query(Alert).filter(
            Alert.sensor_id == sensor.id,
            Alert.greenhouse_id == greenhouse.id,
            Alert.status == AlertStatusEnum.ACTIVE
        ).first()

        if existing_alert:
            existing_alert.severity = severity
            existing_alert.message = message
            existing_alert.trigger_value = val
            existing_alert.threshold_value = threshold_val
            existing_alert.pasos_resolucion = resolution_recipe
            db.add(existing_alert)
            return existing_alert

        # Creamos una nueva alerta activa con su recetario correctivo
        new_alert = Alert(
            greenhouse_id=greenhouse.id,
            sensor_id=sensor.id,
            severity=severity,
            status=AlertStatusEnum.ACTIVE,
            title=f"Alerta en {sensor.name}",
            message=message,
            trigger_value=val,
            threshold_value=threshold_val,
            pasos_resolucion=resolution_recipe,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_alert)
        logger.warning(f"[ALERTA GENERADA] [{severity.value}] {new_alert.title}: {new_alert.message}")
        return new_alert


