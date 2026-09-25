# Hydroponic Greenhouse IoT Platform (HydroGuard) 🌿💧⚡

Plataforma escalable y de bajo coste para el monitoreo inteligente de invernaderos hidropónicos con soporte de suscripción multinivel y motor de alertas tempranas.

---



---

## 📁 Estructura del Proyecto

```
.
├── database/
│   └── schema.sql              # DDL Completo en PostgreSQL con particiones e índices
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py     # Registro, login y asignación de planes
│   │       │   ├── telemetry.py# Ingesta masiva de sensores IoT y disparo de alertas
│   │       │   └── dashboard.py# Dashboard dinámico adaptado al nivel de suscripción
│   │       └── api.py          # Enrutador principal de la API
│   ├── core/
│   │   ├── config.py           # Variables de entorno y ajustes Pydantic
│   │   ├── database.py         # Conexión a PostgreSQL y Session Local
│   │   └── security.py         # Hashing y JWT
│   ├── models/
│   │   └── __init__.py         # Modelos ORM (User, Plan, Device, Sensor, Telemetry, Alert)
│   ├── schemas/
│   │   ├── telemetry.py        # Esquemas de ingesta IoT
│   │   ├── dashboard.py        # Esquemas del dashboard por capas
│   │   ├── alert.py            # Esquemas de alertas y recordatorios
│   │   └── user.py             # Esquemas de usuarios
│   ├── services/
│   │   ├── alert_engine.py     # Motor de evaluación de umbrales y alertas tempranas
│   │   └── dashboard_service.py# Ensamblador de vistas según plan del cliente
│   └── main.py                 # Aplicación principal FastAPI
├── scripts/
│   └── seed_data.py            # Carga de datos demo (usuarios, planes y sensores)
├── .env.example                # Variables de entorno de referencia
├── requirements.txt            # Dependencias de Python
└── README.md
```

---



## 🚀 Guía de Instalación y Ejecución

### 1. Requisitos Previos
- Python 3.10+
- PostgreSQL 14+ (con extensión `pgcrypto` y `uuid-ossp`)

### 2. Configuración del Entorno
```bash
# Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate     # En Windows
# source venv/bin/activate # En Linux/macOS

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
```

### 3. Base de Datos
Ejecutar el script SQL en PostgreSQL:
```bash
psql -U postgres -d hydroponics_db -f database/schema.sql
```

O poblar directamente con el script de Python:
```bash
python scripts/seed_data.py
```

### 4. Ejecutar el Servidor
```bash
uvicorn app.main:app --reload --port 8000
```
- Documentación interactiva Swagger: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`

---

## 📡 Ejemplos de Peticiones a la API

### 1. Ingesta de Telemetría IoT (Microcontrolador ESP32)
`POST /api/v1/telemetry/ingest`
```json
{
  "device_uid": "ESP32-GH-BASE-001",
  "api_key": "secret-iot-key",
  "timestamp": "2026-09-24T18:30:00Z",
  "readings": [
    { "sensor_code": "TANK_PH", "value": 4.8 },
    { "sensor_code": "TANK_TEMP", "value": 21.5 },
    { "sensor_code": "TANK_NUTRIENTS_EC", "value": 1.6 },
    { "sensor_code": "TANK_WATER_LEVEL", "value": 12.0 }
  ],
  "metadata": {
    "battery_node_pct": 95,
    "wifi_rssi_dbm": -68
  }
}
```
*Respuesta:*
```json
{
  "status": "success",
  "processed_readings": 4,
  "triggered_alerts": 2,
  "server_time": "2026-09-24T18:30:01.120Z"
}
```
*(Se dispararon alertas automáticas: pH crítico < 5.0 y Nivel de agua crítico < 15%).*

### 2. Consultar Dashboard Dinámico
`GET /api/v1/dashboard/summary?user_id=<USER_UUID>`

- Si el usuario es **Plan Base**, los campos `generator_module` y `solar_module` retornan `null`.
- Si el usuario es **Plan Estándar**, `generator_module` contendrá combustible y autonomía, mientras `solar_module` será `null`.
- Si el usuario es **Plan Premium**, todos los módulos se retornan con telemetría consolidada en tiempo real.
