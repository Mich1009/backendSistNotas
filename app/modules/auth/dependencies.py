from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
from ...database import get_db
from .models import User, RoleEnum
from .security import verify_token

# Configuración del esquema de autenticación Bearer
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Obtiene el usuario actual basado en el token JWT"""
    token = credentials.credentials
    payload = verify_token(token)
    
    dni: str = payload.get("sub")
    if dni is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.dni == dni).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Obtiene el usuario actual activo"""
    return current_user

def require_roles(allowed_roles: List[RoleEnum]):
    """Decorator para requerir roles específicos"""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para acceder a este recurso"
            )
        return current_user
    return role_checker

# Dependencias específicas por rol
def get_admin_user(current_user: User = Depends(require_roles([RoleEnum.ADMIN]))) -> User:
    """Requiere que el usuario sea administrador"""
    return current_user

def get_docente_user(current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.DOCENTE]))) -> User:
    """Requiere que el usuario sea docente o admin"""
    return current_user

def get_estudiante_user(current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.ESTUDIANTE]))) -> User:
    """Requiere que el usuario sea estudiante o admin"""
    return current_user

def get_any_authenticated_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Requiere cualquier usuario autenticado"""
    return current_user