from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from ...database import get_db
from ..auth.dependencies import get_estudiante_user
from ..auth.models import User
from .models import Carrera, Ciclo, Curso, Matricula

router = APIRouter(tags=["Estudiante - Horario"])

@router.get("/schedule")
def get_student_schedule(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db),
    ciclo_id: Optional[int] = Query(None, description="Filtrar por ciclo específico"),
    año: Optional[int] = Query(None, description="Filtrar por año específico")
):
    """Obtener horario del estudiante"""
    
    try:
        # Obtener matrículas activas del estudiante
        matriculas_query = db.query(Matricula).join(Ciclo).filter(
            Matricula.estudiante_id == current_user.id,
            Matricula.is_active == True
        )
        
        # Aplicar filtros
        if año:
            matriculas_query = matriculas_query.filter(Ciclo.año == año)
        
        if ciclo_id:
            matriculas_query = matriculas_query.filter(Matricula.ciclo_id == ciclo_id)
        
        matriculas_activas = matriculas_query.all()
        
        # Obtener cursos de los ciclos en los que está matriculado
        ciclo_ids = [matricula.ciclo_id for matricula in matriculas_activas]
        
        if not ciclo_ids:
            return []
        
        cursos = db.query(Curso).filter(
            Curso.ciclo_id.in_(ciclo_ids),
            Curso.is_active == True
        ).options(
            joinedload(Curso.ciclo).joinedload(Ciclo.carrera),
            joinedload(Curso.docente)
        ).all()
        
        # Convertir a formato de horario
        horario_response = []
        for curso in cursos:
            horario_data = {
                "id": curso.id,
                "curso_nombre": curso.nombre,
                "docente_nombre": f"{curso.docente.first_name} {curso.docente.last_name}",
                "ciclo_nombre": curso.ciclo.nombre,
                "ciclo_año": curso.ciclo.año,
                "horario": None,  # Campo no implementado aún
                "aula": None,     # Campo no implementado aún
                "carrera_nombre": curso.ciclo.carrera.nombre if curso.ciclo.carrera else None
            }
            
            horario_response.append(horario_data)
        
        return horario_response
        
    except Exception as e:
        print(f"Error in get_student_schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el horario del estudiante"
        )