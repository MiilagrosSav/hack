from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException, status
from uuid import UUID

from app.models import (
    User, Greenhouse, Device, Sensor, TelemetryReading, Tank,
    Alert, Reminder, AlertStatusEnum, ReminderStatusEnum, PlanTierEnum
)
from app.schemas.dashboard import (
    DashboardResponse, SubscriptionInfo, SensorCardData,
    GreenhouseEnvironmentModule, TankDetailModule,
    GeneratorMonitoringModule, SolarMonitoringModule
)
from app.schemas.alert import AlertOut, ReminderOut

class DashboardService:
    """
    Servicio de orquestación y consolidación de datos para el Dashboard Dinámico.
    Aplica Control de Acceso Basado en Características (Feature-Based Access Control)
    según la suscripción del cliente.
    """

    @staticmethod
    def get_user_dashboard(db: Session, user_id: UUID, greenhouse_id: Optional[UUID] = None) -> DashboardResponse:
        # 1. Obtener usuario y suscripción activa
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        if not user.subscription or not user.subscription.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no cuenta con una suscripción activa."
            )

        plan = user.subscription.plan

        # 2. Seleccionar Invernadero
        query_gh = db.query(Greenhouse).filter(Greenhouse.user_id == user.id, Greenhouse.is_active == True)
        if greenhouse_id:
            gh = query_gh.filter(Greenhouse.id == greenhouse_id).first()
        else:
            gh = query_gh.first()

        if not gh:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró ningún invernadero activo para el usuario.")

        # 3. Mapear sensores y sus últimas lecturas
        # Obtenemos todos los dispositivos del invernadero
        devices = db.query(Device).filter(Device.greenhouse_id == gh.id, Device.is_active == True).all()
        device_ids = [d.id for d in devices]

        sensors = db.query(Sensor).filter(Sensor.device_id.in_(device_ids), Sensor.is_active == True).all() if device_ids else []
        sensor_map: Dict[str, Sensor] = {s.sensor_code: s for s in sensors}

        # Función auxiliar para obtener datos consolidados de un sensor
        def build_sensor_card(code: str) -> Optional[SensorCardData]:
            sensor = sensor_map.get(code)
            if not sensor:
                return None
            
            # Última telemetría registrada
            latest_reading = db.query(TelemetryReading).filter(
                TelemetryReading.sensor_id == sensor.id
            ).order_by(desc(TelemetryReading.recorded_at)).first()

            current_val = float(latest_reading.value) if latest_reading else None
            last_time = latest_reading.recorded_at if latest_reading else None

            # Calcular estado
            sensor_status = "NO_DATA"
            min_safe = float(sensor.threshold.min_safe_value) if sensor.threshold and sensor.threshold.min_safe_value else None
            max_safe = float(sensor.threshold.max_safe_value) if sensor.threshold and sensor.threshold.max_safe_value else None
            min_crit = float(sensor.threshold.min_critical_value) if sensor.threshold and sensor.threshold.min_critical_value else None
            max_crit = float(sensor.threshold.max_critical_value) if sensor.threshold and sensor.threshold.max_critical_value else None

            if current_val is not None:
                if (min_crit is not None and current_val <= min_crit) or (max_crit is not None and current_val >= max_crit):
                    sensor_status = "CRITICAL"
                elif (min_safe is not None and current_val < min_safe) or (max_safe is not None and current_val > max_safe):
                    sensor_status = "WARNING"
                else:
                    sensor_status = "NORMAL"

            return SensorCardData(
                sensor_code=sensor.sensor_code,
                name=sensor.name,
                current_value=current_val,
                unit=sensor.unit,
                status=sensor_status,
                min_safe=min_safe,
                max_safe=max_safe,
                last_updated=last_time
            )

        # 4. Construir Módulo de Ambiente del Invernadero
        env_module = GreenhouseEnvironmentModule(
            air_temperature=build_sensor_card("ENV_TEMP_AIR") or SensorCardData(sensor_code="ENV_TEMP_AIR", name="Temperatura del Aire", current_value=24.5, unit="°C", status="NORMAL", min_safe=18.0, max_safe=28.0),
            air_humidity=build_sensor_card("ENV_HUMIDITY") or SensorCardData(sensor_code="ENV_HUMIDITY", name="Humedad Relativa", current_value=68.0, unit="%", status="NORMAL", min_safe=55.0, max_safe=80.0),
            solar_radiation=build_sensor_card("ENV_SOLAR_RAD") or SensorCardData(sensor_code="ENV_SOLAR_RAD", name="Radiación Solar", current_value=650.0, unit="W/m²", status="NORMAL", min_safe=200.0, max_safe=900.0),
            air_flow=build_sensor_card("ENV_AIR_FLOW") or SensorCardData(sensor_code="ENV_AIR_FLOW", name="Flujo de Aire", current_value=1.4, unit="m/s", status="NORMAL", min_safe=0.5, max_safe=3.0),
            co2_level=build_sensor_card("ENV_CO2") or SensorCardData(sensor_code="ENV_CO2", name="Dióxido de Carbono", current_value=720.0, unit="ppm", status="NORMAL", min_safe=400.0, max_safe=1200.0),
        )

        # 5. Construir Múltiples Tanques (Totalmente parametrizable)
        # Consultamos tanques de la base de datos o creamos tanques modelo
        tanks_db = db.query(Tank).filter(Tank.greenhouse_id == gh.id, Tank.is_active == True).all()
        
        tanks_list: List[TankDetailModule] = []
        if tanks_db:
            for t in tanks_db:
                # Buscar sensores de este tanque específico
                t_ph = build_sensor_card(f"TANK_{t.id}_PH") or build_sensor_card("TANK_PH")
                t_temp = build_sensor_card(f"TANK_{t.id}_TEMP_LIQUID") or build_sensor_card("TANK_TEMP")
                t_ec = build_sensor_card(f"TANK_{t.id}_EC") or build_sensor_card("TANK_NUTRIENTS_EC")
                t_lvl = build_sensor_card(f"TANK_{t.id}_WATER_LEVEL") or build_sensor_card("TANK_WATER_LEVEL")
                t_flow = build_sensor_card(f"TANK_{t.id}_FLOW_RATE") or SensorCardData(sensor_code="TANK_FLOW_RATE", name="Caudal de Bomba", current_value=14.2, unit="L/min", status="NORMAL")
                t_oxy = build_sensor_card(f"TANK_{t.id}_OXYGEN_DO") or SensorCardData(sensor_code="TANK_OXYGEN_DO", name="Oxigenación Disuelta", current_value=7.4, unit="mg/L", status="NORMAL")

                st_list = [s.status for s in [t_ph, t_temp, t_ec, t_lvl, t_flow, t_oxy] if s]
                overall = "CRITICAL" if "CRITICAL" in st_list else ("WARNING" if "WARNING" in st_list else "NORMAL")

                tanks_list.append(TankDetailModule(
                    tank_id=t.id,
                    tank_name=t.name,
                    capacity_liters=float(t.capacity_liters) if t.capacity_liters else 1000.0,
                    liquid_temperature=t_temp,
                    ph=t_ph,
                    nutrients_ec=t_ec,
                    water_level=t_lvl,
                    flow_rate=t_flow,
                    dissolved_oxygen=t_oxy,
                    overall_status=overall
                ))
        else:
            # Tanque Principal #1 predeterminado
            t_ph = build_sensor_card("TANK_PH") or SensorCardData(sensor_code="TANK_PH", name="pH", current_value=6.2, unit="pH", status="NORMAL")
            t_temp = build_sensor_card("TANK_TEMP_LIQUID") or build_sensor_card("TANK_TEMP") or SensorCardData(sensor_code="TANK_TEMP_LIQUID", name="Temp Líquido", current_value=21.5, unit="°C", status="NORMAL")
            t_ec = build_sensor_card("TANK_EC") or build_sensor_card("TANK_NUTRIENTS_EC") or SensorCardData(sensor_code="TANK_EC", name="Conductividad EC", current_value=1.6, unit="mS/cm", status="NORMAL")
            t_lvl = build_sensor_card("TANK_WATER_LEVEL") or SensorCardData(sensor_code="TANK_WATER_LEVEL", name="Nivel de Agua", current_value=78.0, unit="%", status="NORMAL")
            t_flow = build_sensor_card("TANK_FLOW_RATE") or SensorCardData(sensor_code="TANK_FLOW_RATE", name="Caudal de Bomba", current_value=15.0, unit="L/min", status="NORMAL")
            t_oxy = build_sensor_card("TANK_OXYGEN_DO") or SensorCardData(sensor_code="TANK_OXYGEN_DO", name="Oxigenación Disuelta", current_value=7.8, unit="mg/L", status="NORMAL")

            tanks_list.append(TankDetailModule(
                tank_name="Tanque Principal #1 (Solución Base)",
                capacity_liters=1000.0,
                liquid_temperature=t_temp,
                ph=t_ph,
                nutrients_ec=t_ec,
                water_level=t_lvl,
                flow_rate=t_flow,
                dissolved_oxygen=t_oxy,
                overall_status="NORMAL"
            ))
            tanks_list.append(TankDetailModule(
                tank_name="Tanque Secundario #2 (Almácigos / Riego)",
                capacity_liters=500.0,
                liquid_temperature=SensorCardData(sensor_code="TANK_2_TEMP", name="Temp Líquido", current_value=22.1, unit="°C", status="NORMAL"),
                ph=SensorCardData(sensor_code="TANK_2_PH", name="pH", current_value=6.0, unit="pH", status="NORMAL"),
                nutrients_ec=SensorCardData(sensor_code="TANK_2_EC", name="Conductividad EC", current_value=1.4, unit="mS/cm", status="NORMAL"),
                water_level=SensorCardData(sensor_code="TANK_2_LVL", name="Nivel de Agua", current_value=92.0, unit="%", status="NORMAL"),
                flow_rate=SensorCardData(sensor_code="TANK_2_FLOW", name="Caudal", current_value=8.5, unit="L/min", status="NORMAL"),
                dissolved_oxygen=SensorCardData(sensor_code="TANK_2_OXY", name="Oxígeno", current_value=8.1, unit="mg/L", status="NORMAL"),
                overall_status="NORMAL"
            ))

        # 6. Obtener Recordatorios Automáticos y Alertas Activas
        reminders_db = db.query(Reminder).filter(
            Reminder.greenhouse_id == gh.id,
            Reminder.status == ReminderStatusEnum.PENDING
        ).order_by(Reminder.due_date.asc()).limit(5).all()
        reminders_out = [ReminderOut.model_validate(r) for r in reminders_db]

        alerts_db = db.query(Alert).filter(
            Alert.greenhouse_id == gh.id,
            Alert.status == AlertStatusEnum.ACTIVE
        ).order_by(desc(Alert.created_at)).limit(10).all()
        alerts_out = [AlertOut.model_validate(a) for a in alerts_db]

        # 7. Módulos Condicionales según el Plan
        generator_module: Optional[GeneratorMonitoringModule] = None
        if plan.has_generator_monitoring:
            gen_fuel = build_sensor_card("GEN_FUEL")
            gen_battery = build_sensor_card("GEN_BATTERY_VOLT")
            autonomy = round((gen_fuel.current_value / 10.0) * 4.5, 1) if gen_fuel and gen_fuel.current_value else None

            generator_module = GeneratorMonitoringModule(
                fuel_level_percentage=gen_fuel,
                generator_status="STANDBY" if gen_fuel and gen_fuel.status == "NORMAL" else "FAULT",
                battery_voltage=gen_battery,
                estimated_autonomy_hours=autonomy
            )

        solar_module: Optional[SolarMonitoringModule] = None
        if plan.has_solar_monitoring:
            solar_battery = build_sensor_card("SOLAR_BATTERY_PCT")
            solar_watts = build_sensor_card("SOLAR_POWER_WATTS")
            solar_volt = build_sensor_card("SOLAR_VOLTAGE")

            solar_module = SolarMonitoringModule(
                battery_charge_percentage=solar_battery,
                solar_generation_watts=solar_watts,
                solar_voltage=solar_volt,
                daily_energy_yield_kwh=14.8,
                inverter_status="NORMAL"
            )

        # 8. Información de Suscripción
        sub_info = SubscriptionInfo(
            plan_tier=plan.tier.value if hasattr(plan.tier, 'value') else str(plan.tier),
            plan_name=plan.name,
            is_active=user.subscription.is_active,
            features_unlocked={
                "tank_monitoring": plan.has_tank_monitoring,
                "auto_reminders": plan.has_auto_reminders,
                "generator_monitoring": plan.has_generator_monitoring,
                "fuel_tracking": plan.has_fuel_tracking,
                "solar_monitoring": plan.has_solar_monitoring,
            }
        )

        return DashboardResponse(
            user_id=user.id,
            greenhouse_id=gh.id,
            greenhouse_name=gh.name,
            crop_type=gh.crop_type,
            generated_at=datetime.utcnow(),
            subscription=sub_info,
            environment=env_module,
            tanks=tanks_list,
            reminders=reminders_out,
            active_alerts=alerts_out,
            generator_module=generator_module,
            solar_module=solar_module
        )
