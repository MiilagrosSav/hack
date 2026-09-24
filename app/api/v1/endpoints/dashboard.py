from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from app.core.database import get_db
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter()

@router.get(
    "/summary",
    response_model=DashboardResponse,
    summary="Dashboard Dinámico Consolidado por Nivel de Suscripción",
    description="Retorna únicamente los módulos y sensores correspondientes al plan del usuario (Base, Estándar, Premium)."
)
def get_dashboard_summary(
    user_id: UUID = Query(..., description="ID del usuario / productor hidropónico"),
    greenhouse_id: Optional[UUID] = Query(None, description="ID del invernadero (opcional, por defecto el principal)"),
    db: Session = Depends(get_db)
):
    """
    Control de Acceso Dinámico:
    - Plan Base: Tanque (pH, Temp, Nivel, Nutrientes) + Recordatorios + Alertas activas.
    - Plan Estándar: Base + Módulo de Generador Eléctrico y Combustible.
    - Plan Premium: Estándar + Módulo de Paneles Solares y Baterías.
    """
    return DashboardService.get_user_dashboard(db=db, user_id=user_id, greenhouse_id=greenhouse_id)
