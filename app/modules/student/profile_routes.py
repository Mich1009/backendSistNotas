from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from ...database import get_db
from ..auth.dependencies import get_estudiante_user
from ..auth.models import User
from .schemas import EstudianteResponse

router = APIRouter(tags=["Estudiante - Perfil"])

@router.get("/profile", response_model=EstudianteResponse)
def get_student_profile(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener perfil del estudiante"""
    
    try:
        # Obtener información del estudiante (el current_user ya es el estudiante)
        estudiante = db.query(User).filter(
            User.id == current_user.id
        ).options(
            joinedload(User.carrera)
        ).first()
        
        if not estudiante:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estudiante no encontrado"
            )
        
        # Convertir a formato de respuesta
        estudiante_data = {
            "id": estudiante.id,
            "user_id": estudiante.id,  # En este caso user_id es el mismo que id
            "codigo_estudiante": estudiante.codigo_estudiante,
            "telefono": estudiante.phone,  # Usar phone del modelo User
            "direccion": estudiante.direccion,
            "fecha_nacimiento": estudiante.fecha_nacimiento,
            "genero": estudiante.genero,
            "estado_civil": estudiante.estado_civil,
            "nombre_completo": f"{estudiante.first_name} {estudiante.last_name}",
            "email": estudiante.email,
            "is_active": estudiante.is_active,
            "created_at": estudiante.created_at,
            "updated_at": estudiante.updated_at
        }
        
        return estudiante_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_student_profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el perfil del estudiante"
        )