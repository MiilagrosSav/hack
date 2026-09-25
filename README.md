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
