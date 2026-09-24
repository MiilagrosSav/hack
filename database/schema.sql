-- =============================================================================
-- PROYECTO: Sistema IoT de Monitoreo de Invernaderos Hidropónicos
-- BASE DE DATOS: PostgreSQL (Compatible con TimescaleDB si se requiere extensión)
-- AUTOR: Arquitectura de Software & IoT Solutions
-- =============================================================================

-- Extensiones recomendadas
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- 1. TIPOS ENUMERADOS (ENUMS)
-- =============================================================================

CREATE TYPE plan_tier_enum AS ENUM ('BASE', 'ESTANDAR', 'PREMIUM');
CREATE TYPE user_role_enum AS ENUM ('ADMIN', 'PRODUCER', 'OPERATOR');
CREATE TYPE sensor_category_enum AS ENUM ('TANQUE', 'GENERADOR', 'PANELES_SOLARES', 'AMBIENTAL');
CREATE TYPE alert_severity_enum AS ENUM ('INFO', 'WARNING', 'CRITICAL');
CREATE TYPE alert_status_enum AS ENUM ('ACTIVE', 'ACKNOWLEDGED', 'RESOLVED');
CREATE TYPE reminder_status_enum AS ENUM ('PENDING', 'SENT', 'COMPLETED', 'CANCELLED');

-- =============================================================================
-- 2. TABLAS DE SUSCRIPCIÓN Y USUARIOS
-- =============================================================================

CREATE TABLE plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    tier plan_tier_enum NOT NULL UNIQUE,
    description TEXT,
    price_monthly NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    -- Capacidades del plan (Flags de funcionalidad)
    has_tank_monitoring BOOLEAN NOT NULL DEFAULT TRUE,
    has_auto_reminders BOOLEAN NOT NULL DEFAULT TRUE,
    has_generator_monitoring BOOLEAN NOT NULL DEFAULT FALSE,
    has_fuel_tracking BOOLEAN NOT NULL DEFAULT FALSE,
    has_solar_monitoring BOOLEAN NOT NULL DEFAULT FALSE,
    max_devices INTEGER NOT NULL DEFAULT 2,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone_number VARCHAR(30),
    role user_role_enum NOT NULL DEFAULT 'PRODUCER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    start_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_active_sub UNIQUE (user_id)
);

-- =============================================================================
-- 3. GESTIÓN DE INVERNADEROS Y DISPOSITIVOS HARDWARE
-- =============================================================================

CREATE TABLE greenhouses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    location_description TEXT,
    crop_type VARCHAR(100) DEFAULT 'Lechuga Hidropónica / Nutrientes NFT',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    greenhouse_id UUID NOT NULL REFERENCES greenhouses(id) ON DELETE CASCADE,
    device_uid VARCHAR(100) NOT NULL UNIQUE, -- Código de Hardware (MAC / Serial / UUID)
    api_key_hash VARCHAR(255) NOT NULL,      -- Hash para autenticación rápida del microcontrolador (ESP32/Raspberry Pi)
    model VARCHAR(100) DEFAULT 'ESP32-HydroGuard-v1',
    firmware_version VARCHAR(50) DEFAULT '1.0.0',
    last_heartbeat TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sensors (
    id SERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    sensor_code VARCHAR(50) NOT NULL, -- Ej: TANK_TEMP, TANK_PH, TANK_NUTRIENTS_EC, TANK_WATER_LEVEL, GEN_FUEL, SOLAR_VOLTAGE, SOLAR_CHARGE_PCT
    name VARCHAR(100) NOT NULL,
    category sensor_category_enum NOT NULL,
    unit VARCHAR(20) NOT NULL,        -- Ej: '°C', 'pH', 'mS/cm', 'cm', '%', 'V', 'A'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_device_sensor_code UNIQUE (device_id, sensor_code)
);

-- Umbrales de Seguridad para Alertas Tempranas (Configurables por sensor o invernadero)
CREATE TABLE sensor_thresholds (
    id SERIAL PRIMARY KEY,
    sensor_id INTEGER NOT NULL REFERENCES sensors(id) ON DELETE CASCADE,
    min_safe_value NUMERIC(10, 2),
    max_safe_value NUMERIC(10, 2),
    min_critical_value NUMERIC(10, 2),
    max_critical_value NUMERIC(10, 2),
    warning_message TEXT,
    critical_message TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_sensor_threshold UNIQUE (sensor_id)
);

-- =============================================================================
-- 4. TELEMETRÍA Y MEDICIONES (Optimizado para Series Temporales)
-- =============================================================================

CREATE TABLE telemetry_readings (
    id BIGSERIAL,
    sensor_id INTEGER NOT NULL REFERENCES sensors(id) ON DELETE CASCADE,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    value NUMERIC(10, 3) NOT NULL,
    raw_payload JSONB, -- Metadatos adicionales opcionales (batería del nodo, RSSI wifi, etc.)
    PRIMARY KEY (id, recorded_at)
) PARTITION BY RANGE (recorded_at);

-- Particiones por rango temporal (Ejemplo mensual - automatizable)
CREATE TABLE telemetry_readings_2026_09 PARTITION OF telemetry_readings
    FOR VALUES FROM ('2026-09-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');

CREATE TABLE telemetry_readings_2026_10 PARTITION OF telemetry_readings
    FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');

CREATE TABLE telemetry_readings_default PARTITION OF telemetry_readings
    DEFAULT;

-- Índices estratégicos para consultas rápidas del Dashboard
CREATE INDEX idx_telemetry_sensor_time ON telemetry_readings (sensor_id, recorded_at DESC);
CREATE INDEX idx_telemetry_device_time ON telemetry_readings (device_id, recorded_at DESC);

-- =============================================================================
-- 5. SISTEMA DE ALERTAS Y RECORDATORIOS
-- =============================================================================

CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    greenhouse_id UUID NOT NULL REFERENCES greenhouses(id) ON DELETE CASCADE,
    sensor_id INTEGER REFERENCES sensors(id) ON DELETE SET NULL,
    severity alert_severity_enum NOT NULL DEFAULT 'WARNING',
    status alert_status_enum NOT NULL DEFAULT 'ACTIVE',
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    trigger_value NUMERIC(10, 3),
    threshold_value NUMERIC(10, 3),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_alerts_greenhouse_status ON alerts (greenhouse_id, status, created_at DESC);

CREATE TABLE reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    greenhouse_id UUID NOT NULL REFERENCES greenhouses(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    due_date TIMESTAMPTZ NOT NULL,
    status reminder_status_enum NOT NULL DEFAULT 'PENDING',
    recurrence_interval_days INTEGER DEFAULT 0, -- 0 = No recurrente, 7 = semanal, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_reminders_user_due ON reminders (user_id, due_date, status);

-- =============================================================================
-- 6. SEMILLAS DE DATOS INICIALES (PLANS CATALOG)
-- =============================================================================

INSERT INTO plans (name, tier, description, price_monthly, has_tank_monitoring, has_auto_reminders, has_generator_monitoring, has_fuel_tracking, has_solar_monitoring, max_devices)
VALUES 
('Plan Básico Hidropónico', 'BASE', 'Monitoreo esencial de variables en tanque (pH, Temperatura, EC, Nivel de agua) y recordatorios automáticos de nutrición y mantenimiento.', 19.99, TRUE, TRUE, FALSE, FALSE, FALSE, 2),
('Plan Estándar Energético', 'ESTANDAR', 'Todo el Plan Base + Monitoreo de Generador Eléctrico, estados de marcha y nivel de combustible en tiempo real.', 39.99, TRUE, TRUE, TRUE, TRUE, FALSE, 5),
('Plan Premium Total', 'PREMIUM', 'Todo el Plan Estándar + Monitoreo avanzado de Paneles Solares, estado de carga de baterías y eficiencia energética.', 59.99, TRUE, TRUE, TRUE, TRUE, TRUE, 10)
ON CONFLICT (name) DO NOTHING;
