import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import hashlib
from datetime import datetime, timedelta
from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models import (
    Plan, User, UserSubscription, Greenhouse, Tank, Device, Sensor,
    SensorThreshold, TelemetryReading, Alert, Reminder,
    PlanTierEnum, UserRoleEnum, SensorCategoryEnum, ReminderStatusEnum, AlertSeverityEnum, AlertStatusEnum
)
from app.services.alert_engine import AlertEngine

def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

def seed():
    print("[+] Creando tablas en PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    print("[+] Iniciando carga de datos iniciales...")

    try:
        # 1. Asegurar Planes
        plans = {
            PlanTierEnum.BASE: Plan(
                name="Plan Básico Hidropónico",
                tier=PlanTierEnum.BASE,
                description="Monitoreo de Tanques (pH, Temp, EC, Nivel, Caudal, Oxígeno) + Microclima + Alertas",
                price_monthly=19.99,
                has_tank_monitoring=True,
                has_auto_reminders=True,
                has_generator_monitoring=False,
                has_fuel_tracking=False,
                has_solar_monitoring=False,
                max_devices=2
            ),
            PlanTierEnum.ESTANDAR: Plan(
                name="Plan Estándar Energético",
                tier=PlanTierEnum.ESTANDAR,
                description="Todo Plan Base + Monitoreo de Generador Eléctrico y Nivel de Diésel",
                price_monthly=39.99,
                has_tank_monitoring=True,
                has_auto_reminders=True,
                has_generator_monitoring=True,
                has_fuel_tracking=True,
                has_solar_monitoring=False,
                max_devices=5
            ),
            PlanTierEnum.PREMIUM: Plan(
                name="Plan Premium Total",
                tier=PlanTierEnum.PREMIUM,
                description="Todo Plan Estándar + Monitoreo de Paneles Solares y Banco de Baterías Litio",
                price_monthly=59.99,
                has_tank_monitoring=True,
                has_auto_reminders=True,
                has_generator_monitoring=True,
                has_fuel_tracking=True,
                has_solar_monitoring=True,
                max_devices=10
            )
        }

        for tier, plan_obj in plans.items():
            existing = db.query(Plan).filter(Plan.tier == tier).first()
            if not existing:
                db.add(plan_obj)
        db.commit()

        # 2. Configuración de Usuarios por Nivel
        users_config = [
            {"email": "base@hydroguard.io", "name": "Carlos Productor (Plan Base)", "tier": PlanTierEnum.BASE},
            {"email": "estandar@hydroguard.io", "name": "María Invernaderos (Plan Estándar)", "tier": PlanTierEnum.ESTANDAR},
            {"email": "premium@hydroguard.io", "name": "AgroTech Enterprise (Plan Premium)", "tier": PlanTierEnum.PREMIUM},
        ]

        for u_cfg in users_config:
            user = db.query(User).filter(User.email == u_cfg["email"]).first()
            if not user:
                user = User(
                    email=u_cfg["email"],
                    password_hash=get_password_hash("password123"),
                    full_name=u_cfg["name"],
                    phone_number="+5491145678900",
                    role=UserRoleEnum.PRODUCER
                )
                db.add(user)
                db.flush()

                plan = db.query(Plan).filter(Plan.tier == u_cfg["tier"]).first()
                sub = UserSubscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    is_active=True
                )
                db.add(sub)
                
                # Invernadero
                gh = Greenhouse(
                    user_id=user.id,
                    name="Invernadero #1 (Oberá, Misiones)",
                    location_description="Módulo Hidropónico Automatizado NFT",
                    crop_type="Lechuga Mantecosa & Albahaca"
                )
                db.add(gh)
                db.flush()

                # Dispositivo IoT ESP32
                dev_uid = f"ESP32-GH-{u_cfg['tier'].value}-001"
                device = Device(
                    greenhouse_id=gh.id,
                    device_uid=dev_uid,
                    api_key_hash=hash_key("secret-iot-key"),
                    model="ESP32-HydroGuard-Pro",
                    firmware_version="2.4.0",
                    last_heartbeat=datetime.utcnow()
                )
                db.add(device)
                db.flush()

                # 4 Tanques
                tanks_def = [
                    {"name": "Tanque Principal #1", "cap": 1000.0, "is_crit": True},
                    {"name": "Tanque Secundario #2 (Almácigos)", "cap": 500.0, "is_crit": False},
                    {"name": "Tanque #3 (Línea Forraje)", "cap": 800.0, "is_crit": False},
                    {"name": "Tanque #4 (Cámara Germinación)", "cap": 300.0, "is_crit": False},
                ]
                
                created_tanks = []
                for t_info in tanks_def:
                    t_obj = Tank(
                        greenhouse_id=gh.id,
                        name=t_info["name"],
                        capacity_liters=t_info["cap"]
                    )
                    db.add(t_obj)
                    db.flush()
                    created_tanks.append((t_obj, t_info["is_crit"]))

                # Sensores de Microclima Invernadero
                env_sensors_data = [
                    ("ENV_TEMP_AIR", "Temperatura del Aire", "°C", 24.5, 18.0, 28.0, 12.0, 35.0),
                    ("ENV_HUMIDITY", "Humedad Relativa", "%", 68.0, 55.0, 80.0, 35.0, 95.0),
                    ("ENV_SOLAR_RAD", "Radiación Solar", "W/m²", 650.0, 200.0, 900.0, None, 1200.0),
                    ("ENV_CO2", "Dióxido de Carbono", "ppm", 720.0, 400.0, 1000.0, None, 1800.0),
                    ("ENV_AIR_FLOW", "Flujo de Aire", "m/s", 1.4, 0.5, 3.0, 0.2, 5.0),
                ]

                for code, name, unit, val, s_min, s_max, c_min, c_max in env_sensors_data:
                    s = Sensor(device_id=device.id, sensor_code=code, name=name, category=SensorCategoryEnum.AMBIENTAL, unit=unit)
                    db.add(s)
                    db.flush()
                    thresh = SensorThreshold(sensor_id=s.id, min_safe_value=s_min, max_safe_value=s_max, min_critical_value=c_min, max_critical_value=c_max)
                    db.add(thresh)
                    db.add(TelemetryReading(sensor_id=s.id, device_id=device.id, value=val, recorded_at=datetime.utcnow()))

                # Sensores para cada Tanque
                for idx, (tank_obj, is_crit) in enumerate(created_tanks, start=1):
                    ph_val = 7.2 if is_crit else 6.0
                    lvl_val = 25.0 if is_crit else (90.0 if idx == 2 else (85.0 if idx == 3 else 95.0))
                    
                    tank_metrics = [
                        (f"TANK_{idx}_PH", f"pH Tanque #{idx}", "pH", ph_val, 5.5, 6.5, 5.0, 7.0, "pH fuera de rango", "¡pH en niveles críticos!"),
                        (f"TANK_{idx}_EC", f"Conductividad EC #{idx}", "mS/cm", 1.6 if idx==1 else 1.2, 1.2, 2.0, 0.8, 2.5, "EC fuera de rango", "EC crítica"),
                        (f"TANK_{idx}_WATER_LEVEL", f"Nivel de Agua #{idx}", "%", lvl_val, 35.0, 100.0, 28.0, 100.0, "Nivel de agua bajo", "¡Nivel de agua crítico!"),
                        (f"TANK_{idx}_TEMP_LIQUID", f"Temp Líquido #{idx}", "°C", 21.5 if idx==1 else 22.0, 18.0, 24.0, 15.0, 28.0, "Temp líquido no óptima", "Temp crítica"),
                        (f"TANK_{idx}_FLOW_RATE", f"Caudal Bomba #{idx}", "L/min", 14.2 if idx==1 else 10.0, 10.0, 18.0, 5.0, 25.0, "Caudal bajo", "Falla de caudal"),
                        (f"TANK_{idx}_OXYGEN_DO", f"Oxígeno Disuelto #{idx}", "mg/L", 7.4 if idx==1 else 7.8, 6.5, 12.0, 5.0, 15.0, "Oxígeno bajo", "Oxígeno crítico"),
                    ]

                    for code, name, unit, val, s_min, s_max, c_min, c_max, w_msg, c_msg in tank_metrics:
                        s = Sensor(device_id=device.id, tank_id=tank_obj.id, sensor_code=code, name=name, category=SensorCategoryEnum.TANQUE, unit=unit)
                        db.add(s)
                        db.flush()
                        thresh = SensorThreshold(sensor_id=s.id, min_safe_value=s_min, max_safe_value=s_max, min_critical_value=c_min, max_critical_value=c_max, warning_message=w_msg, critical_message=c_msg)
                        db.add(thresh)
                        db.add(TelemetryReading(sensor_id=s.id, device_id=device.id, value=val, recorded_at=datetime.utcnow()))

                        # Si tiene anomalía, evaluar alerta
                        AlertEngine.evaluate_reading(db=db, sensor=s, greenhouse=gh, reading_value=val)

                # Sensores Generador (Planes Estándar y Premium)
                if u_cfg["tier"] in [PlanTierEnum.ESTANDAR, PlanTierEnum.PREMIUM]:
                    gen_sensors = [
                        ("GEN_FUEL", "Nivel de Combustible Diésel", "%", 78.0, 35.0, 100.0, 15.0, 100.0),
                        ("GEN_BATTERY_VOLT", "Batería de Arranque Generador", "V", 12.8, 12.4, 13.5, 11.5, 14.5),
                        ("GEN_AUTONOMY", "Autonomía Estimada", "hrs", 18.5, 8.0, 50.0, 3.0, 60.0),
                        ("GEN_VOLTAGE", "Tensión Generador", "V", 220.0, 210.0, 230.0, 190.0, 250.0),
                        ("GEN_HOURS", "Horómetro Motor", "hrs", 142.0, 0.0, 200.0, 0.0, 250.0),
                    ]
                    for code, name, unit, val, s_min, s_max, c_min, c_max in gen_sensors:
                        s = Sensor(device_id=device.id, sensor_code=code, name=name, category=SensorCategoryEnum.GENERADOR, unit=unit)
                        db.add(s)
                        db.flush()
                        thresh = SensorThreshold(sensor_id=s.id, min_safe_value=s_min, max_safe_value=s_max, min_critical_value=c_min, max_critical_value=c_max)
                        db.add(thresh)
                        db.add(TelemetryReading(sensor_id=s.id, device_id=device.id, value=val, recorded_at=datetime.utcnow()))

                # Sensores Solares (Plan Premium)
                if u_cfg["tier"] == PlanTierEnum.PREMIUM:
                    solar_sensors = [
                        ("SOLAR_BATTERY_PCT", "Carga Banco de Baterías Litio", "%", 92.0, 40.0, 100.0, 20.0, 100.0),
                        ("SOLAR_POWER_WATTS", "Potencia Generada Paneles", "W", 4200.0, 1500.0, 5500.0, None, 6000.0),
                        ("SOLAR_VOLTAGE", "Voltaje String Solar", "V", 148.0, 120.0, 180.0, 90.0, 200.0),
                        ("SOLAR_YIELD_KWH", "Rendimiento Diario Acumulado", "kWh", 24.8, 18.0, 40.0, None, 50.0),
                        ("SOLAR_CONSUMPTION", "Consumo Bombas Invernadero", "kW", 1.8, 0.5, 3.5, None, 5.0),
                        ("SOLAR_EFFICIENCY", "Eficiencia Inversor Híbrido", "%", 97.4, 95.0, 99.5, 90.0, 100.0),
                    ]
                    for code, name, unit, val, s_min, s_max, c_min, c_max in solar_sensors:
                        s = Sensor(device_id=device.id, sensor_code=code, name=name, category=SensorCategoryEnum.PANELES_SOLARES, unit=unit)
                        db.add(s)
                        db.flush()
                        thresh = SensorThreshold(sensor_id=s.id, min_safe_value=s_min, max_safe_value=s_max, min_critical_value=c_min, max_critical_value=c_max)
                        db.add(thresh)
                        db.add(TelemetryReading(sensor_id=s.id, device_id=device.id, value=val, recorded_at=datetime.utcnow()))

                # Recordatorios
                db.add(Reminder(
                    greenhouse_id=gh.id,
                    user_id=user.id,
                    title="Dosificación Nutrientes Solución A+B",
                    description="Revisar concentración y añadir sales concentradas según fase fenológica.",
                    due_date=datetime.utcnow() + timedelta(days=2),
                    recurrence_interval_days=7
                ))

        db.commit()
        print("[SUCCESS] Base de datos poblada exitosamente con todos los sensores, rangos y lecturas.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error al poblar base de datos: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed()
