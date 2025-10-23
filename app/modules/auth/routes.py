from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ...database import get_db
from .models import User, PasswordResetToken
from .schemas import UserLogin, Token, UserResponse, PasswordReset, PasswordResetConfirm, ChangePassword, UserUpdate, TokenVerificationResponse, TokenVerificationRequest
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
        
        import secrets
        
        # ✅ GENERAR DOS TOKENS
        identificator_token = secrets.token_urlsafe(16)  # Corto para URL
        verification_token = secrets.token_urlsafe(32)   # Largo para verificación
        
        print(f"🎯 DEBUG: Identificator Token: {identificator_token}")
        print(f"🎯 DEBUG: Verification Token: {verification_token}")
        
        db_token = PasswordResetToken(
            user_id=user.id,
            identificator_token=identificator_token,
            token=verification_token,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.add(db_token)
        db.commit()
        print("🎯 DEBUG: Tokens guardados en BD")
        
        # ✅ IMPRIMIR PARA PRUEBAS
        print("🔐" * 40)
        print(f"🎯 IDENTIFICATOR TOKEN (URL): {identificator_token}")
        print(f"🎯 VERIFICATION TOKEN: {verification_token}")
        print(f"📧 EMAIL: {user.email}")
        print("🔐" * 40)
        
        # Enviar email con el identificator_token en la URL
        reset_url = f"http://localhost:5173/password-reset?token={identificator_token}"
        email_recuperacion.send_password_reset_email(user.email, reset_url)
        
    else:
        print(f"🎯 DEBUG: Usuario NO encontrado para: {password_reset.email}")
    
    return {"message": "Si el email existe, recibirás un enlace de recuperación"}

@router.post("/password-reset/confirm")
def confirm_password_reset(password_reset_confirm: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Cambiar contraseña usando el verification_token"""
    
    # Buscar por verification_token
    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == password_reset_confirm.verification_token,
        PasswordResetToken.expires_at > datetime.utcnow(),
        PasswordResetToken.used == False
    ).first()
    
    if not db_token:
        raise HTTPException(status_code=400, detail="Token de verificación inválido o expirado")
    
    # Marcar token como usado
    db_token.used = True
    
    # Actualizar contraseña
    db_token.user.hashed_password = get_password_hash(password_reset_confirm.new_password)
    db.commit()
    
    return {"message": "Contraseña actualizada exitosamente"}

@router.post("/password-reset/verify", response_model=TokenVerificationResponse)
def verify_reset_token(token_data: TokenVerificationRequest, db: Session = Depends(get_db)):
    """Verificar si un identificator_token es válido y obtener el verification_token"""
    
    print("🎯 DEBUG: Llegó request a /verify")
    print(f"🎯 DEBUG: token_data recibido: {token_data}")
    print(f"🎯 DEBUG: token_data.token: {token_data.token}")
    print(f"🎯 DEBUG: Tipo de token: {type(token_data.token)}")

    #identificator_token = token_data.get("token")
    
    if not token_data.token:
        print("❌ DEBUG: Token vacío o None")
        return TokenVerificationResponse(
            valid=False, 
            message="Token no proporcionado"
        )
    
    # Buscar por identificator_token
    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.identificator_token == token_data.token,
        PasswordResetToken.expires_at > datetime.utcnow(),
        PasswordResetToken.used == False
    ).first()
    
    if not db_token:
        return TokenVerificationResponse(
            valid=False, 
            message="Token inválido o expirado"
        )
    
    return TokenVerificationResponse(
        valid=True,
        message="Token válido",
        verification_token=db_token.token,  # Este se usa para cambiar la contraseña
        email=db_token.user.email
    )

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