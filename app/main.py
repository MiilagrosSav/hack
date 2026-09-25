from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import engine, Base
from app.services.mqtt_service import mqtt_service

# Crear tablas si no existen (en caso de pruebas rápidas sin migraciones de Alembic)
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicio: Iniciar cliente MQTT en segundo plano
    mqtt_service.start()
    yield
    # Cierre: Detener cliente MQTT
    mqtt_service.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    description="""
    ## API de Monitoreo Inteligente de Invernaderos Hidropónicos 🌿💧
    
    ### Características Principales:
    - **Ingesta de Telemetría IoT en Tiempo Real con MQTT (Mosquitto/EMQX) y QoS 1**.
    - **Motor de Asistencia Pasiva**: Detección inmediata y recetario agronómico con cálculo de dosis exactas.
    - **Dashboard Dinámico Adaptativo**: Filtrado de datos por suscripción (**Plan Base**, **Plan Estándar**, **Plan Premium**).
    - **Gestión de Recordatorios Automáticos** de mantenimiento y dosificación.
    """,
    version="1.0.0"
)

# Configuración de CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

# Configuración de Archivos Estáticos del Frontend
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
def serve_dashboard():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "HydroGuard IoT Backend Running. Visit /docs for API documentation."}

@app.get("/health", tags=["Salud del Sistema"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
