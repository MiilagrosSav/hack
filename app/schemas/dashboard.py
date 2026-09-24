from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from app.schemas.alert import AlertOut, ReminderOut

class SensorCardData(BaseModel):
    sensor_code: str
    name: str
    current_value: Optional[float]
    unit: str
    status: str # 'NORMAL', 'WARNING', 'CRITICAL', 'NO_DATA'
    min_safe: Optional[float] = None
    max_safe: Optional[float] = None
    last_updated: Optional[datetime] = None

class GreenhouseEnvironmentModule(BaseModel):
    """Sensores ambientales propios del invernadero"""
    air_temperature: Optional[SensorCardData] = None  # Temp aire °C
    air_humidity: Optional[SensorCardData] = None     # Humedad %
    solar_radiation: Optional[SensorCardData] = None  # Radiación W/m²
    air_flow: Optional[SensorCardData] = None         # Flujo de aire m/s
    co2_level: Optional[SensorCardData] = None        # CO2 ppm

class TankDetailModule(BaseModel):
    """Sensores individuales propios de cada tanque de solución nutritiva"""
    tank_id: Optional[UUID] = None
    tank_name: str # e.g. "Tanque Principal #1"
    capacity_liters: Optional[float] = 1000.0
    liquid_temperature: Optional[SensorCardData] = None # Temp líquido °C
    ph: Optional[SensorCardData] = None                 # pH
    nutrients_ec: Optional[SensorCardData] = None       # Conductividad EC mS/cm
    water_level: Optional[SensorCardData] = None        # Cantidad de agua % o L
    flow_rate: Optional[SensorCardData] = None          # Caudal L/min
    dissolved_oxygen: Optional[SensorCardData] = None   # Aireación / Oxigenación mg/L o %
    overall_status: str = "NORMAL"

class GeneratorMonitoringModule(BaseModel):
    fuel_level_percentage: Optional[SensorCardData] = None
    generator_status: str = "OFFLINE" # 'RUNNING', 'STANDBY', 'OFFLINE', 'FAULT'
    battery_voltage: Optional[SensorCardData] = None
    estimated_autonomy_hours: Optional[float] = None

class SolarMonitoringModule(BaseModel):
    battery_charge_percentage: Optional[SensorCardData] = None
    solar_generation_watts: Optional[SensorCardData] = None
    solar_voltage: Optional[SensorCardData] = None
    daily_energy_yield_kwh: Optional[float] = None
    inverter_status: str = "NORMAL"

class SubscriptionInfo(BaseModel):
    plan_tier: str # 'BASE', 'ESTANDAR', 'PREMIUM'
    plan_name: str
    is_active: bool
    features_unlocked: Dict[str, bool]

class DashboardResponse(BaseModel):
    user_id: UUID
    greenhouse_id: UUID
    greenhouse_name: str
    crop_type: str
    generated_at: datetime
    subscription: SubscriptionInfo
    
    # Módulos del Invernadero y Tanques
    environment: GreenhouseEnvironmentModule
    tanks: List[TankDetailModule]
    
    # Notificaciones y Tareas
    reminders: List[ReminderOut]
    active_alerts: List[AlertOut]
    
    # Módulos Condicionales según Plan
    generator_module: Optional[GeneratorMonitoringModule] = None # Solo ESTANDAR y PREMIUM
    solar_module: Optional[SolarMonitoringModule] = None        # Solo PREMIUM
