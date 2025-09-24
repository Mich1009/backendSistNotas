from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
from .models import RoleEnum

class UserLogin(BaseModel):
    dni: str
    password: str
    
    @validator('dni')
    def validate_dni(cls, v):
        if not v.isdigit() or len(v) != 8:
            raise ValueError('DNI debe tener exactamente 8 dígitos')
        return v

class Token(BaseModel):
    access_token: str
    token_type: str
    user: 'UserResponse'

class TokenData(BaseModel):
    dni: Optional[str] = None

class UserBase(BaseModel):
    dni: str
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: RoleEnum
    
    @validator('dni')
    def validate_dni(cls, v):
        if not v.isdigit() or len(v) != 8:
            raise ValueError('DNI debe tener exactamente 8 dígitos')
        return v

class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('La contraseña debe tener al menos 6 caracteres')
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('La contraseña debe tener al menos 6 caracteres')
        return v

class ChangePassword(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('La contraseña debe tener al menos 6 caracteres')
        return v