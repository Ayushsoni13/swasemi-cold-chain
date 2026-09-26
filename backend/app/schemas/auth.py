from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.enums import RoleEnum

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: str
    organization_id: Optional[str] = None
    email: EmailStr
    role: RoleEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
