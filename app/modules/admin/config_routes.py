from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import base64
import uuid
import shutil
from ...database import get_db
from ..auth.dependencies import get_admin_user
from ...shared.config_models import SiteConfig
from pydantic import BaseModel

router = APIRouter(prefix="/config", tags=["Admin - Configuración"])

# Directorio para guardar las imágenes
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ConfigResponse(BaseModel):
    id: int
    key: str
    value: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

class ConfigCreate(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class ConfigUpdate(BaseModel):
    value: str
    description: Optional[str] = None

@router.get("/logo", response_model=ConfigResponse)
async def get_logo_config(
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    """Obtiene la configuración del logo (requiere autenticación de admin)"""
    config = db.query(SiteConfig).filter(SiteConfig.key == "login_logo").first()
    if not config:
        # Crear configuración por defecto si no existe
        config = SiteConfig(
            key="login_logo",
            value="/static/uploads/default-logo.png",
            description="Logo mostrado en la página de login"
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return config

@router.get("/public/logo", response_model=ConfigResponse)
async def get_public_logo_config(
    db: Session = Depends(get_db)
):
    """Obtiene la configuración del logo (endpoint público)"""
    config = db.query(SiteConfig).filter(SiteConfig.key == "login_logo").first()
    if not config:
        # Crear configuración por defecto si no existe
        config = SiteConfig(
            key="login_logo",
            value="/static/uploads/default-logo.png",
            description="Logo mostrado en la página de login"
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return config

@router.put("/logo", response_model=ConfigResponse)
async def update_logo_config(
    config_update: ConfigUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    """Actualiza la configuración del logo"""
    config = db.query(SiteConfig).filter(SiteConfig.key == "login_logo").first()
    
    # Verificar si es una URL externa o una imagen en base64
    value = config_update.value
    if value.startswith('data:image'):
        # Es una imagen en base64, guardarla como archivo
        try:
            # Extraer el tipo de imagen y los datos
            format_data, imgstr = value.split(';base64,')
            ext = format_data.split('/')[-1]
            
            # Generar nombre único para el archivo
            filename = f"logo_{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            
            # Guardar la imagen como archivo
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(imgstr))
            
            # Actualizar el valor en la base de datos para que sea la ruta al archivo
            file_url = f"/static/uploads/{filename}"
            value = file_url
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al procesar la imagen: {str(e)}"
            )
    
    if not config:
        config = SiteConfig(
            key="login_logo",
            value=value,
            description=config_update.description or "Logo mostrado en la página de login"
        )
        db.add(config)
    else:
        config.value = value
        if config_update.description:
            config.description = config_update.description
    
    db.commit()
    db.refresh(config)
    return config

@router.get("/", response_model=List[ConfigResponse])
async def get_all_configs(
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    """Obtiene todas las configuraciones del sistema"""
    configs = db.query(SiteConfig).all()
    return configs