from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import base64
import uuid
import shutil
import glob
from ...database import get_db
from ..auth.dependencies import get_admin_user
from ...shared.models import SiteConfig
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
    
    # Guardar la ruta del logo anterior para eliminarlo después
    old_logo_path = None
    if config and config.value and config.value.startswith('/static/uploads/'):
        # Extraer el nombre del archivo del logo anterior
        old_filename = config.value.replace('/static/uploads/', '')
        old_logo_path = os.path.join(UPLOAD_DIR, old_filename)
    
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
    
    # Guardar los cambios en la base de datos primero
    db.commit()
    db.refresh(config)
    
    # Limpiar automáticamente todos los logos antiguos después de guardar el nuevo
    if value.startswith('/static/uploads/'):
        try:
            cleanup_result = cleanup_unused_logo_files(db)
            if cleanup_result["success"] and cleanup_result["deleted_count"] > 0:
                print(f"Limpieza automática completada: {cleanup_result['deleted_count']} archivos eliminados")
        except Exception as e:
            print(f"Error durante la limpieza automática de logos: {str(e)}")
            # No lanzar excepción aquí para no afectar la operación principal
    
    return config

@router.get("/", response_model=List[ConfigResponse])
async def get_all_configs(
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    """Obtiene todas las configuraciones del sistema"""
    configs = db.query(SiteConfig).all()
    return configs

def cleanup_unused_logo_files(db: Session) -> dict:
    """
    Limpia archivos de logo no utilizados del directorio de uploads
    Retorna un diccionario con estadísticas de la limpieza
    """
    try:
        # Obtener la configuración actual del logo
        config = db.query(SiteConfig).filter(SiteConfig.key == "login_logo").first()
        current_logo_file = None
        
        if config and config.value and config.value.startswith('/static/uploads/'):
            current_logo_file = config.value.replace('/static/uploads/', '')
        
        # Buscar todos los archivos de logo en el directorio
        logo_pattern = os.path.join(UPLOAD_DIR, "logo_*")
        all_logo_files = glob.glob(logo_pattern)
        
        deleted_files = []
        errors = []
        
        for file_path in all_logo_files:
            filename = os.path.basename(file_path)
            
            # Si no es el logo actual, eliminarlo
            if filename != current_logo_file:
                try:
                    os.remove(file_path)
                    deleted_files.append(filename)
                    print(f"Archivo de logo no utilizado eliminado: {filename}")
                except Exception as e:
                    error_msg = f"Error al eliminar {filename}: {str(e)}"
                    errors.append(error_msg)
                    print(error_msg)
        
        return {
            "success": True,
            "current_logo": current_logo_file,
            "deleted_files": deleted_files,
            "deleted_count": len(deleted_files),
            "errors": errors,
            "message": f"Limpieza completada. {len(deleted_files)} archivos eliminados."
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Error durante la limpieza de archivos"
        }

@router.post("/logo/cleanup")
async def cleanup_logo_files(
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    """
    Endpoint para limpiar archivos de logo no utilizados
    Solo accesible por administradores
    """
    result = cleanup_unused_logo_files(db)
    
    if result["success"]:
        return {
            "message": result["message"],
            "details": {
                "current_logo": result["current_logo"],
                "deleted_files": result["deleted_files"],
                "deleted_count": result["deleted_count"],
                "errors": result["errors"]
            }
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )