from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from ...database import get_db
from ..auth.dependencies import get_docente_user
from ..auth.models import User
from ..auth.security import verify_password, get_password_hash
from .schemas import DocenteProfileUpdate, PasswordUpdate

router = APIRouter()

@router.get("/profile")
def get_teacher_profile(
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener perfil del docente"""
    return {
        "id": current_user.id,
        "dni": current_user.dni,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "especialidad": current_user.especialidad,
        "grado_academico": current_user.grado_academico,
        "fecha_ingreso": current_user.fecha_ingreso,
        "is_active": current_user.is_active,
        "role": current_user.role
    }

@router.put("/profile")
def update_teacher_profile(
    profile_data: DocenteProfileUpdate,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Actualizar perfil del docente"""
    
    # Verificar si el email ya existe (si se está cambiando)
    if profile_data.email and profile_data.email != current_user.email:
        existing_user = db.query(User).filter(User.email == profile_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
    
    # Actualizar campos
    if profile_data.first_name:
        current_user.first_name = profile_data.first_name
    if profile_data.last_name:
        current_user.last_name = profile_data.last_name
    if profile_data.email:
        current_user.email = profile_data.email
    if profile_data.phone:
        current_user.phone = profile_data.phone
    if profile_data.especialidad:
        current_user.especialidad = profile_data.especialidad
    if profile_data.grado_academico:
        current_user.grado_academico = profile_data.grado_academico
    
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Perfil actualizado correctamente",
        "user": {
            "id": current_user.id,
            "dni": current_user.dni,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "especialidad": current_user.especialidad,
            "grado_academico": current_user.grado_academico,
            "fecha_ingreso": current_user.fecha_ingreso,
            "is_active": current_user.is_active,
            "role": current_user.role
        }
    }

@router.put("/change-password")
def change_password(
    password_data: PasswordUpdate,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Cambiar contraseña del docente"""
    
    # Verificar contraseña actual
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta"
        )
    
    # Verificar que las nuevas contraseñas coincidan
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las nuevas contraseñas no coinciden"
        )
    
    # Verificar que la nueva contraseña sea diferente a la actual
    if verify_password(password_data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe ser diferente a la actual"
        )
    
    # Actualizar contraseña
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Contraseña actualizada correctamente"
    }