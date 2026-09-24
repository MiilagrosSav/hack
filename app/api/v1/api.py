from fastapi import APIRouter
from app.api.v1.endpoints import telemetry, dashboard, auth, simulation

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
api_router.include_router(telemetry.router, prefix="/telemetry", tags=["Telemetría IoT"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard Dinámico"])
api_router.include_router(simulation.router, prefix="/simulation", tags=["Simulación & Parámetros"])

