from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class SensorReadingItem(BaseModel):
    sensor_code: str = Field(..., example="TANK_PH", description="Código identificador del sensor (ej. TANK_PH, TANK_TEMP, TANK_WATER_LEVEL, GEN_FUEL, SOLAR_VOLTAGE)")
    value: float = Field(..., example=6.25, description="Valor numérico leído por el sensor")

class TelemetryIngestPayload(BaseModel):
    device_uid: str = Field(..., example="ESP32-GH-TANK-001", description="Identificador único del microcontrolador/dispositivo")
    api_key: str = Field(..., example="secret-node-key-abc123xyz", description="Clave de autenticación del dispositivo IoT")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Timestamp de captura")
    readings: List[SensorReadingItem] = Field(..., description="Lista de mediciones de sensores enviadas en lote")
    metadata: Optional[Dict[str, Any]] = Field(default=None, example={"battery_pct": 98, "wifi_rssi": -65})

class TelemetryIngestResponse(BaseModel):
    status: str = "success"
    processed_readings: int
    triggered_alerts: int
    server_time: datetime = Field(default_factory=datetime.utcnow)
