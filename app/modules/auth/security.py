from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import hashlib
import os
from fastapi import HTTPException, status
from ...config import settings

# Función para generar un salt aleatorio
def generate_salt(length=16):
    """Genera un salt aleatorio para el hash"""
    return os.urandom(length).hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña plana coincide con el hash"""
    # El formato del hash es: algoritmo$salt$hash
    parts = hashed_password.split('$')
    if len(parts) != 3:
        return False
    
    algorithm, salt, stored_hash = parts
    
    # Recrear el hash con la contraseña proporcionada
    computed_hash = hashlib.sha256((plain_password + salt).encode()).hexdigest()
    
    # Comparar los hashes
    return computed_hash == stored_hash

def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña usando SHA-256 con salt
    
    Esta implementación evita los problemas de bcrypt con contraseñas largas
    """
    # Generar un salt aleatorio
    salt = generate_salt()
    
    # Crear el hash
    hash_value = hashlib.sha256((password + salt).encode()).hexdigest()
    
    # Devolver en formato: algoritmo$salt$hash
    return f"sha256${salt}${hash_value}"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT de acceso"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str):
    """Verifica y decodifica un token JWT"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

def create_password_reset_token(email: str) -> str:
    """Crea un token para reseteo de contraseña"""
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode = {"sub": email, "exp": expire, "type": "password_reset"}
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_password_reset_token(token: str) -> str:
    """Verifica un token de reseteo de contraseña"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido"
            )
        return email
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado"
        )