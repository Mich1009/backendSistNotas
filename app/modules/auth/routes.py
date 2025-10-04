from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ...database import get_db
from .models import User
from .schemas import UserLogin, Token, UserResponse, PasswordReset, PasswordResetConfirm, ChangePassword, UserUpdate
from .security import verify_password, get_password_hash, create_access_token, verify_password_reset_token
from .dependencies import get_current_active_user

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Endpoint para iniciar sesión con DNI y contraseña"""
    
    # Buscar usuario por DNI
    user = db.query(User).filter(User.dni == user_credentials.dni).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="DNI o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar contraseña
    if not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="DNI o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar que el usuario esté activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    
    # Actualizar último login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Crear token de acceso
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.dni}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/password-reset")
def request_password_reset(password_reset: PasswordReset, db: Session = Depends(get_db)):
    """Solicitar reseteo de contraseña por email"""
    
    user = db.query(User).filter(User.email == password_reset.email).first()
    
    if not user:
        # Por seguridad, no revelamos si el email existe o no
        return {"message": "Si el email existe, recibirás un enlace de recuperación"}
    
    # TODO: Implementar envío de email con token
    # Por ahora solo retornamos un mensaje
    
    return {"message": "Si el email existe, recibirás un enlace de recuperación"}

@router.post("/password-reset/confirm")
def confirm_password_reset(
    password_reset_confirm: PasswordResetConfirm, 
    db: Session = Depends(get_db)
):
    """Confirmar reseteo de contraseña con token"""
    
    # Verificar token
    email = verify_password_reset_token(password_reset_confirm.token)
    
    # Buscar usuario
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Actualizar contraseña
    user.hashed_password = get_password_hash(password_reset_confirm.new_password)
    db.commit()
    
    return {"message": "Contraseña actualizada exitosamente"}

@router.post("/change-password")
def change_password(
    password_change: ChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cambiar contraseña del usuario actual"""
    
    # Verificar contraseña actual
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta"
        )
    
    # Actualizar contraseña
    current_user.hashed_password = get_password_hash(password_change.new_password)
    db.commit()
    
    return {"message": "Contraseña cambiada exitosamente"}

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Obtener información del usuario actual"""
    return current_user

@router.put("/me", response_model=UserResponse)
def update_current_user_info(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Actualizar información del usuario actual"""
    
    # Actualizar solo los campos proporcionados
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    # Actualizar timestamp
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.post("/logout")
def logout():
    """Cerrar sesión (invalidar token del lado del cliente)"""
    return {"message": "Sesión cerrada exitosamente"}