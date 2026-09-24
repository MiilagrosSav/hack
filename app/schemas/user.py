from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    plan_tier: str

class UserLogin(BaseModel):
    email: str = Field(..., example="usuario@ejemplo.com")
    password: str

class UserCreate(BaseModel):
    email: str = Field(..., example="usuario@ejemplo.com")
    password: str
    full_name: str
    phone_number: Optional[str] = None
    plan_tier: str = "BASE" # 'BASE', 'ESTANDAR', 'PREMIUM'
