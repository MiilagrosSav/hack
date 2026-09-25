from typing import List, Union, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl

class Settings(BaseSettings):
    PROJECT_NAME: str = "Hydroponic Greenhouse IoT Platform"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = "hydro-secret-key-production-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 horas

    # Conexión a PostgreSQL
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/hydroponics_db"

    # Configuración de Broker MQTT para Nodos IoT (ESP32)
    MQTT_BROKER_HOST: str = "localhost" # Broker MQTT (Mosquitto / EMQX / HiveMQ)
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_KEEPALIVE: int = 60
    MQTT_CLIENT_ID: str = "hydroguard-backend-subscriber"
    MQTT_BASE_TOPIC: str = "hydroguard" # Tópico raíz: hydroguard/gh/+/devices/+/telemetry
    MQTT_ENABLED: bool = True

    # CORS
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000"
    ]

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
