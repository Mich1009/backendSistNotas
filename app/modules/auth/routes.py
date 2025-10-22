from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ...database import get_db
from .models import User, PasswordResetToken
from .schemas import UserLogin, Token, UserResponse, PasswordReset, PasswordResetConfirm, ChangePassword, UserUpdate
from .security import verify_password, get_password_hash, create_access_token, verify_password_reset_token, create_password_reset_token
from .dependencies import get_current_active_user
from ...shared.email_recuperacion import email_recuperacion

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
    print("🎯 DEBUG: Entrando a /password-reset")
    print(f"🎯 DEBUG: Email recibido: {password_reset.email}")
    
    user = db.query(User).filter(User.email == password_reset.email).first()
    
    if user:
        print(f"🎯 DEBUG: Usuario encontrado: {user.email}")
        
        reset_token = create_password_reset_token(user.email)
        print(f"🎯 DEBUG: Token generado: {reset_token}")
        
        db_token = PasswordResetToken(
            user_id=user.id,
            token=reset_token,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.add(db_token)
        db.commit()
        print("🎯 DEBUG: Token guardado en BD")
        
        # ✅ ESTO DEBE IMPRIMIRSE
        print("🔐" * 30)
        print(f"🎯 TOKEN PARA COPIAR: {reset_token}")
        print(f"📧 EMAIL: {user.email}")
        print("🔐" * 30)
        
        # Enviar email
        email_recuperacion.send_password_reset_email(user.email, reset_token)
        
    else:
        print(f"🎯 DEBUG: Usuario NO encontrado para: {password_reset.email}")
    
    return {"message": "Si el email existe, recibirás un enlace de recuperación"}

@router.post("/password-reset/confirm")
def confirm_password_reset(password_reset_confirm: PasswordResetConfirm, db: Session = Depends(get_db)):
    try:
        # ✅ VERIFICAR TOKEN JWT (CON MANEJO DE ERRORES)
        email = verify_password_reset_token(password_reset_confirm.token)
    except HTTPException:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # ✅ VERIFICAR EN TABLA PasswordResetToken (NUEVO)
    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == password_reset_confirm.token,
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.expires_at > datetime.utcnow(),
        PasswordResetToken.used == False
    ).first()
    
    if not db_token:
        raise HTTPException(status_code=400, detail="Token inválido o ya utilizado")
    
    # ✅ MARCAR TOKEN COMO USADO (NUEVO)
    db_token.used = True
    
    user.hashed_password = get_password_hash(password_reset_confirm.new_password)
    db.commit()
    
    return {"message": "Contraseña actualizada exitosamente"}

@router.post("/password-reset/verify-token")
def verify_reset_token(token_data: dict, db: Session = Depends(get_db)):
    """Verificar si un token de recuperación es válido"""
    try:
        email = verify_password_reset_token(token_data["token"])
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            return {"valid": False, "message": "Usuario no encontrado"}
        
        # Verificar en la tabla de tokens
        db_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token_data["token"],
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.expires_at > datetime.utcnow(),
            PasswordResetToken.used == False
        ).first()
        
        return {
            "valid": db_token is not None,
            "email": email if db_token else None,
            "message": "Token válido" if db_token else "Token inválido o expirado"
        }
        
    except HTTPException:
        return {"valid": False, "message": "Token inválido"}
    
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