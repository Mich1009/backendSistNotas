from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Base de datos - PostgreSQL
    # Usa DATABASE_URL del archivo .env, con fallback por defecto
    database_url: str = "postgresql://postgres:password@localhost:5432/sistema_notas"
    
    # JWT
    # Usa SECRET_KEY del archivo .env, con fallback por defecto
    secret_key: str = "fallback_secret_key_change_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS - Se parseará automáticamente desde el .env
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Email
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    
    # General
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Permite que pydantic parsee automáticamente listas desde strings JSON
        json_encoders = {
            list: lambda v: v if isinstance(v, list) else eval(v) if isinstance(v, str) else v
        }

settings = Settings()