# 🌿 HydroGuard IoT — Documentación Técnica del Software

Sistema Integral de Monitoreo Inteligente y Asistencia Pasiva para Invernaderos Hidropónicos con Telemetría IoT en Tiempo Real sobre MQTT y PostgreSQL.

---

## 1. 📌 Resumen Ejecutivo y Propósito

**HydroGuard** es una solución tecnológica de nivel industrial diseñada para evitar pérdidas productivas catastróficas en invernaderos hidropónicos (sistemas NFT, raíz flotante y sustrato). 

A diferencia de los sistemas tradicionales de automatización ciega (que inyectan químicos automáticamente con alto riesgo de sobredosificación por fallas en válvulas), HydroGuard opera bajo el principio de **Asistencia Pasiva**:
1. **Monitorea en tiempo real** variables químicas, hidráulicas, microclimáticas y energéticas mediante nodos IoT distribuidos.
2. **Detecta anomalías en milisegundos** antes de que causen estrés o mortandad radicular.
3. **Calcula la receta de corrección exacta** (dosificación en mililitros de buffers pH+, pH-, fertilizantes A/B o reposición de agua en litros según el volumen real del tanque).
4. **Guía al productor paso a paso** en una interfaz amigable, garantizando control y seguridad agronómica.

---

## 2. 🏛️ Arquitectura General del Sistema

```mermaid
flowchart TB
    subgraph Hardware_Layer [1. Capa de Sensores y Hardware Industrial]
        Modbus_1[Sensores Modbus RS485 Tanques<br>pH, EC, Temp, Nivel, Caudal, O₂]
        Modbus_2[Sensores Modbus RS485 Clima<br>Temp Aire, Humedad, Rad, CO₂]
        Modbus_3[Sensores Modbus RS485 Energía<br>Diésel Generador, Inversor Solar]
    end

    subgraph Ingestion_Layer [2. Capa de Conectividad e Ingesta de Datos]
        Waveshare["Módulo Waveshare RS485 TO ETH<br>Lectura Modbus RTU & Transmisión Directa HTTP POST<br>(Ethernet Cableado RJ45 - Sin Microcontrolador Intermedio)"]
        Broker["MQTT Broker Opcional (Mosquitto/EMQX)<br>Para Nodos Inalámbricos Distribuidos"]
    end

    subgraph Backend_Layer [3. Capa de Backend & Inteligencia]
        FastAPI_App["API REST FastAPI (/api/v1/telemetry/ingest)<br>(Python 3.14 + Uvicorn)"]
        Alert_Engine["Motor de Asistencia Pasiva<br>(Fórmulas Matemáticas de Dosificación)"]
        MQTT_Sub["Servicio Suscriptor MQTT<br>(paho-mqtt)"]
    end

    subgraph Data_Layer [4. Capa de Persistencia]
        Postgres[("PostgreSQL Database<br>• telemetry_readings (Particionada)<br>• sensor_thresholds & alerts<br>• plans, users & greenhouses")]
    end

    subgraph Presentation_Layer [5. Capa de Presentación]
        Dashboard["Dashboard Web Interactivo<br>• Selector Cíclico de Planes<br>• Panel de Acción con Recetas<br>• Alto Contraste Mobile-First"]
    end

    Modbus_1 --> Waveshare
    Modbus_2 --> Waveshare
    Modbus_3 --> Waveshare

    Waveshare -- "HTTP POST (JSON directo vía Ethernet)" --> FastAPI_App
    Broker -- "Topic Subscription" --> MQTT_Sub
    
    FastAPI_App --> Alert_Engine
    MQTT_Sub --> Alert_Engine
    Alert_Engine --> Postgres
    FastAPI_App <--> Postgres
    FastAPI_App <--> Dashboard
```

---

## 3. ⚙️ Explicación del Funcionamiento

### 3.1 Conectividad Industrial e Ingesta de Datos
El sistema implementa una arquitectura de ingesta robusta de grado industrial:

1. **Ingesta Directa Ethernet Industrial (Principal):**
   - El **Módulo Waveshare RS485 TO ETH** realiza el escaneo periódico de los registros Modbus RTU de todos los sensores del invernadero (pH, conductividad eléctrica EC, temperatura del agua, boyas de nivel, sensores climáticos y monitores de energía).
   - Ensambla y transmite directamente las lecturas en formato JSON hacia el endpoint REST de FastAPI (`POST /api/v1/telemetry/ingest`) a través de red Ethernet cableada (RJ45).
   - **Ventaja clave:** Elimina la necesidad de microcontroladores intermedios (como microprocesadores adicionales propensos a reinicios o fallas de memoria), garantizando inmunidad a interferencias electromagnéticas y máxima estabilidad industrial 24/7.

2. **Ingesta Inalámbrica IoT (Opcional):**
   - Compatible adicionalmente con nodos inalámbricos que publiquen telemetría vía broker **MQTT (QoS 1)**.

```json
// Ejemplo de Payload JSON transmitido por el módulo Waveshare RS485 TO ETH:
{
  "device_uid": "WAVESHARE-RS485-ETH-001",
  "api_key": "secret-iot-key",
  "readings": [
    { "sensor_code": "TANK_1_PH", "value": 5.0 },
    { "sensor_code": "TANK_1_WATER_LEVEL", "value": 25.0 },
    { "sensor_code": "TANK_1_EC", "value": 1.6 },
    { "sensor_code": "ENV_TEMP_AIR", "value": 24.5 }
  ]
}
```

### 3.2 El Motor de Asistencia Pasiva (`AlertEngine`)
Cuando el endpoint de FastAPI recibe la lectura del conversor Waveshare:
1. Compara el valor contra los umbrales seguros (`min_safe_value`, `max_safe_value`) y críticos (`min_critical_value`, `max_critical_value`) configurados en `sensor_thresholds`.
2. Si detecta una desviación, **calcula dinámicamente la receta agronómica**:
   - **pH Ácido (< 5.5):** Calcula la dosis en ml de Buffer Incrementador ($\text{Dosis} = \frac{\text{Volumen Tanque}}{100} \times \Delta pH \times 20\text{ ml}$).
   - **pH Alcalino (> 6.5):** Calcula la dosis en ml de Reductor Ácido Fosfórico ($\text{Dosis} = \frac{\text{Volumen Tanque}}{100} \times \Delta pH \times 24\text{ ml}$).
   - **Nivel de Agua Bajo (< 35%):** Calcula los litros exactos necesarios para alcanzar el 85% de capacidad.
   - **Nutrientes EC Bajos (< 1.2 mS/cm):** Calcula los mililitros exactos de Solución A y Solución B a dosificar.
   - **Combustible Diésel Bajo (< 35%):** Calcula los litros de diésel para llenar el depósito y protocolo de purga.
3. Almacena la receta en el campo `pasos_resolucion` de la tabla `alerts` en PostgreSQL.

### 3.3 Modelo de Suscripciones Dinámico
El sistema adapta su interfaz y el monitoreo según el plan activo:
- 🌱 **Plan Base ($19.99/mes):** Monitoreo de 4 tanques hidropónicos (pH, EC, nivel, caudal, temperatura líquida, oxígeno) + microclima (temperatura de aire, humedad, radiación, CO₂) + recordatorios automáticos de fertilización.
- ⚡ **Plan Estándar ($39.99/mes):** Todo lo del Plan Base + Monitoreo de Generador Diésel de emergencia, nivel de combustible y autonomía restante.
- 👑 **Plan Premium ($59.99/mes):** Todo lo del Plan Estándar + Monitoreo de Sistema Solar Fotovoltaico (potencia generada, tensión de strings, rendimiento diario kWh) y Banco de Baterías de Litio (% de carga).

---

## 4. 💻 Tecnologías Utilizadas

### A. Capa de Conectividad e Ingesta de Datos
- **Tecnología:** **HTTP POST (Módulo Waveshare RS485 TO ETH)**.
- **Función en el Proyecto:** El módulo conversor lee los sensores Modbus y transmite directamente los datos en formato JSON al endpoint REST de FastAPI mediante red Ethernet cableada, sin necesidad de microcontroladores intermedios.
- **Protocolo de Sensores:** Modbus RTU sobre bus industrial RS485.
- **Protocolo de Transporte de Red:** HTTP/1.1 REST sobre Ethernet cableada (RJ45, TCP/IP).
- **Transporte Alternativo IoT:** MQTT v3.1.1 / v5 (Eclipse Mosquitto) para nodos inalámbricos auxiliares.

### B. Capa de Backend
- **Lenguaje:** Python 3.14.
- **Framework Web Asíncrono:** **FastAPI** (OpenAPI / Swagger automático, alto rendimiento I/O).
- **Endpoint de Ingesta:** `POST /api/v1/telemetry/ingest` (compatibilidad nativa con Waveshare RS485-ETH).
- **Motor de Reglas:** `AlertEngine` con recetario correctivo de asistencia pasiva.
- **Validación y Esquemas:** **Pydantic v2**.
- **ORM / Persistencia:** **SQLAlchemy 2.0** con sesiones transaccionales seguras.
- **Seguridad:** Criptografía con `passlib` (Bcrypt) y hashing SHA-256 para autenticación de dispositivos/gateways.

### C. Capa de Base de Datos
- **Motor:** **PostgreSQL 15+**.
- **Optimización Temporal:** Tabla `telemetry_readings` particionada por rangos temporales (`PARTITION BY RANGE (recorded_at)`).
- **Extensiones:** `uuid-ossp` y `pgcrypto` para identificadores universales seguros.

### D. Capa de Frontend
- **Estructura:** HTML5 Semántico con estándares de accesibilidad (ARIA).
- **Estilos:** Vanilla CSS moderno con arquitectura de tokens de diseño, paleta esmeralda/bosque de alto contraste para visibilidad bajo luz solar directa en campo.
- **Interactividad:** JavaScript ES6 Vanilla reactivo (Fetch API, manipulación del DOM en tiempo real, modales de calibración y acordeones de recetas paso a paso).

---

## 5. 🚀 Guía de Puesta en Marcha

### 5.1 Requisitos Previos
1. Python 3.10 o superior instalado.
2. PostgreSQL activo con base de datos `hydroponics_db`.
3. (Opcional) Broker MQTT local (*Mosquitto*) corriendo en el puerto `1883`.

### 5.2 Configuración del Entorno (`.env`)
Crear o editar el archivo `.env` en la raíz del proyecto:
```ini
PROJECT_NAME="HydroGuard IoT Platform"
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/hydroponics_db"
MQTT_BROKER_HOST="localhost"
MQTT_BROKER_PORT=1883
MQTT_BASE_TOPIC="hydroguard"
MQTT_ENABLED=True
```

### 5.3 Instalación de Dependencias y Carga de Datos Iniciales
```bash
# 1. Instalar dependencias
pip install -r requirements.txt
pip install paho-mqtt python-pptx

# 2. Poblar base de datos PostgreSQL con datos unificados
python scripts/seed_data.py
```

### 5.4 Iniciar Servidor de Desarrollo
```bash
python -m uvicorn app.main:app --reload --port 8000
```

- **Dashboard Web:** `http://127.0.0.1:8000/` o `http://127.0.0.1:8000/dashboard`
- **Documentación Swagger API:** `http://127.0.0.1:8000/docs`

---

## 6. 📁 Estructura del Proyecto

```
hack/
├── app/
│   ├── api/v1/
│   │   ├── endpoints/
│   │   │   ├── simulation.py      # Control en vivo de estado y alertas
│   │   │   ├── telemetry.py       # Ingesta HTTP de respaldo
│   │   │   └── ...
│   ├── core/
│   │   ├── config.py              # Configuración (PostgreSQL + MQTT)
│   │   └── database.py            # Motor SQLAlchemy
│   ├── models/                    # Modelos relacionales PostgreSQL
│   └── services/
│       ├── alert_engine.py        # Motor de Asistencia Pasiva y Recetarios
│       └── mqtt_service.py        # Suscriptor MQTT en segundo plano
├── database/
│   └── schema.sql                 # Script DDL completo de PostgreSQL
├── firmware/
│   └── esp32_hydroguard_mqtt.ino  # Firmware C++ para microcontrolador ESP32
├── frontend/
│   ├── index.html                 # Interfaz de usuario interactiva
│   ├── style.css                  # Sistema de diseño y estilos responsive
│   └── app.js                     # Lógica reactiva del cliente
├── scripts/
│   ├── seed_data.py               # Generador de datos iniciales en BD
│   └── generate_pitch_deck.py     # Generador de presentación PPTX
├── HydroGuard_Pitch_Hackathon.pptx# Presentación ejecutiva del Hackathon
└── DOCUMENTACION_SOFTWARE.md      # Este documento técnico
```
