from pydantic_settings import BaseSettings
from typing import List
import os
import json

class Settings(BaseSettings):
    # Base de datos - PostgreSQL
    # Usa DATABASE_URL del archivo .env, con fallback por defecto
    database_url: str = "postgresql://postgres:edichogenial@localhost:5432/sistema_notas"
    # JWT
    # Usa SECRET_KEY del archivo .env, con fallback por defecto
    secret_key: str = "fallback_secret_key_change_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS - Se parseará automáticamente desde el .env
    cors_origins: str = '["http://localhost:3000", "http://localhost:5173"]'
    
    # Email
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    
    # General
    debug: bool = True
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parsea la lista de orígenes CORS desde string JSON"""
        try:
            if isinstance(self.cors_origins, str):
                return json.loads(self.cors_origins)
            return self.cors_origins
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "latin-1"
        case_sensitive = False

settings = Settings()