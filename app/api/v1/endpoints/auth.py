from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models import User, Plan, UserSubscription, PlanTierEnum
from app.schemas.user import UserCreate, UserLogin, Token

router = APIRouter()

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    # 1. Verificar si el usuario ya existe
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El correo electrónico ya está registrado.")

    # 2. Buscar plan seleccionado
    plan = db.query(Plan).filter(Plan.tier == payload.plan_tier).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Plan '{payload.plan_tier}' no válido.")

    # 3. Crear usuario
    user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name,
        phone_number=payload.phone_number
    )
    db.add(user)
    db.flush()

    # 4. Asignar suscripción
    sub = UserSubscription(
        user_id=user.id,
        plan_id=plan.id,
        is_active=True
    )
    db.add(sub)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id))
    return Token(access_token=token, token_type="bearer", user_id=user.id, plan_tier=plan.tier.value)

@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    
    plan_tier = user.subscription.plan.tier.value if user.subscription and user.subscription.plan else "BASE"
    token = create_access_token(subject=str(user.id))
    return Token(access_token=token, token_type="bearer", user_id=user.id, plan_tier=plan_tier)
