import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Integer,
    Numeric, Text, Enum as SQLEnum, BigInteger, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

# Enums
class PlanTierEnum(str, enum.Enum):
    BASE = "BASE"
    ESTANDAR = "ESTANDAR"
    PREMIUM = "PREMIUM"

class UserRoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    PRODUCER = "PRODUCER"
    OPERATOR = "OPERATOR"

class SensorCategoryEnum(str, enum.Enum):
    TANQUE = "TANQUE"
    GENERADOR = "GENERADOR"
    PANELES_SOLARES = "PANELES_SOLARES"
    AMBIENTAL = "AMBIENTAL"

class AlertSeverityEnum(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class AlertStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"

class ReminderStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    tier = Column(SQLEnum(PlanTierEnum, name="plan_tier_enum"), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    price_monthly = Column(Numeric(10, 2), default=0.00, nullable=False)

    # Feature Flags para el Dynamic Dashboard y Reglas de Negocio
    has_tank_monitoring = Column(Boolean, default=True, nullable=False)
    has_auto_reminders = Column(Boolean, default=True, nullable=False)
    has_generator_monitoring = Column(Boolean, default=False, nullable=False)
    has_fuel_tracking = Column(Boolean, default=False, nullable=False)
    has_solar_monitoring = Column(Boolean, default=False, nullable=False)
    max_devices = Column(Integer, default=2, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    subscriptions = relationship("UserSubscription", back_populates="plan")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    phone_number = Column(String(30), nullable=True)
    role = Column(SQLEnum(UserRoleEnum, name="user_role_enum"), default=UserRoleEnum.PRODUCER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    subscription = relationship("UserSubscription", back_populates="user", uselist=False)
    greenhouses = relationship("Greenhouse", back_populates="user", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    start_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="subscription")
    plan = relationship("Plan", back_populates="subscriptions")


class Greenhouse(Base):
    __tablename__ = "greenhouses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    location_description = Column(Text, nullable=True)
    crop_type = Column(String(100), default="Lechuga Hidropónica / Nutrientes NFT")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="greenhouses")
    tanks = relationship("Tank", back_populates="greenhouse", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="greenhouse", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="greenhouse", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="greenhouse", cascade="all, delete-orphan")


class Tank(Base):
    __tablename__ = "tanks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    greenhouse_id = Column(UUID(as_uuid=True), ForeignKey("greenhouses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False) # ej: "Tanque Principal #1", "Tanque Solución B"
    capacity_liters = Column(Numeric(10, 2), default=1000.0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    greenhouse = relationship("Greenhouse", back_populates="tanks")
    sensors = relationship("Sensor", back_populates="tank", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    greenhouse_id = Column(UUID(as_uuid=True), ForeignKey("greenhouses.id", ondelete="CASCADE"), nullable=False)
    device_uid = Column(String(100), unique=True, index=True, nullable=False)
    api_key_hash = Column(String(255), nullable=False)
    model = Column(String(100), default="ESP32-HydroGuard-v1")
    firmware_version = Column(String(50), default="1.0.0")
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    greenhouse = relationship("Greenhouse", back_populates="devices")
    sensors = relationship("Sensor", back_populates="device", cascade="all, delete-orphan")


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    tank_id = Column(UUID(as_uuid=True), ForeignKey("tanks.id", ondelete="CASCADE"), nullable=True) # Si pertenece a un tanque
    sensor_code = Column(String(50), nullable=False) 
    # Códigos Tanque: TANK_PH, TANK_TEMP_LIQUID, TANK_EC, TANK_WATER_LEVEL, TANK_FLOW_RATE, TANK_OXYGEN_DO
    # Códigos Ambiente Invernadero: ENV_TEMP_AIR, ENV_HUMIDITY, ENV_CO2, ENV_SOLAR_RAD, ENV_AIR_FLOW
    name = Column(String(100), nullable=False)
    category = Column(SQLEnum(SensorCategoryEnum, name="sensor_category_enum"), nullable=False)
    unit = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    device = relationship("Device", back_populates="sensors")
    tank = relationship("Tank", back_populates="sensors")
    threshold = relationship("SensorThreshold", back_populates="sensor", uselist=False, cascade="all, delete-orphan")
    readings = relationship("TelemetryReading", back_populates="sensor", cascade="all, delete-orphan")


class SensorThreshold(Base):
    __tablename__ = "sensor_thresholds"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id", ondelete="CASCADE"), unique=True, nullable=False)
    min_safe_value = Column(Numeric(10, 2), nullable=True)
    max_safe_value = Column(Numeric(10, 2), nullable=True)
    min_critical_value = Column(Numeric(10, 2), nullable=True)
    max_critical_value = Column(Numeric(10, 2), nullable=True)
    warning_message = Column(Text, nullable=True)
    critical_message = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    sensor = relationship("Sensor", back_populates="threshold")


class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    value = Column(Numeric(10, 3), nullable=False)
    raw_payload = Column(JSONB, nullable=True)

    sensor = relationship("Sensor", back_populates="readings")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    greenhouse_id = Column(UUID(as_uuid=True), ForeignKey("greenhouses.id", ondelete="CASCADE"), nullable=False, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True)
    severity = Column(SQLEnum(AlertSeverityEnum, name="alert_severity_enum"), default=AlertSeverityEnum.WARNING, nullable=False)
    status = Column(SQLEnum(AlertStatusEnum, name="alert_status_enum"), default=AlertStatusEnum.ACTIVE, nullable=False)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    trigger_value = Column(Numeric(10, 3), nullable=True)
    threshold_value = Column(Numeric(10, 3), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    greenhouse = relationship("Greenhouse", back_populates="alerts")
    sensor = relationship("Sensor")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    greenhouse_id = Column(UUID(as_uuid=True), ForeignKey("greenhouses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(SQLEnum(ReminderStatusEnum, name="reminder_status_enum"), default=ReminderStatusEnum.PENDING, nullable=False)
    recurrence_interval_days = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    greenhouse = relationship("Greenhouse", back_populates="reminders")
    user = relationship("User", back_populates="reminders")

