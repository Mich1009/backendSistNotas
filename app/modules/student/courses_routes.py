from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from ...database import get_db
from ..auth.dependencies import get_estudiante_user
from ..auth.models import User
from .models import Carrera, Ciclo, Curso, Matricula, Nota
from .schemas import (
    CursoEstudianteResponse, 
    MatriculaResponse
)

router = APIRouter(tags=["Estudiante - Cursos"])

@router.get("/courses/filters")
def get_student_courses_filters(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener ciclos disponibles basados en las matrículas del estudiante"""
    
    try:
        # Obtener ciclos únicos de las matrículas del estudiante
        # Desde el primer ciclo hasta el ciclo más alto al que se ha matriculado
        ciclos_query = db.query(Ciclo.numero).join(Matricula).filter(
            Matricula.estudiante_id == current_user.id,
            Matricula.is_active == True,
            Ciclo.numero.isnot(None)
        ).distinct().order_by(Ciclo.numero.asc()).all()
        
        ciclos_disponibles = [ciclo[0] for ciclo in ciclos_query if ciclo[0]]
        
        return {
            "ciclos": ciclos_disponibles
        }
        
    except Exception as e:
        print(f"Error in get_student_courses_filters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener los filtros de cursos"
        )

@router.get("/courses", response_model=List[CursoEstudianteResponse])
def get_student_courses(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db),
    ciclo_id: Optional[int] = Query(None, description="Filtrar por ciclo específico"),
    numero_ciclo: Optional[int] = Query(None, description="Filtrar por número de ciclo (1, 2, 3, etc.)")
):
    """Obtener cursos del estudiante con filtros de ciclo"""
    
    try:
        # Obtener matrículas activas del estudiante
        matriculas_query = db.query(Matricula).join(Ciclo).filter(
            Matricula.estudiante_id == current_user.id,
            Matricula.is_active == True
        )
        
        # Aplicar filtros
        if ciclo_id:
            matriculas_query = matriculas_query.filter(Matricula.ciclo_id == ciclo_id)
        
        if numero_ciclo:
            matriculas_query = matriculas_query.filter(Ciclo.numero == numero_ciclo)
        
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
        
        # Convertir a formato de respuesta
        cursos_response = []
        for curso in cursos:
            curso_data = {
                "id": curso.id,
                "nombre": curso.nombre,
                "docente_nombre": f"{curso.docente.first_name} {curso.docente.last_name}",
                "ciclo_nombre": curso.ciclo.nombre,
                "ciclo_año": curso.ciclo.año,
                "ciclo_numero": curso.ciclo.numero,
                "fecha_inicio": curso.ciclo.fecha_inicio.strftime("%Y-%m-%d") if curso.ciclo.fecha_inicio else None,
                "fecha_fin": curso.ciclo.fecha_fin.strftime("%Y-%m-%d") if curso.ciclo.fecha_fin else None,
                "horario": None,  # Campo no implementado aún
                "aula": None,     # Campo no implementado aún
                "carrera_nombre": curso.ciclo.carrera.nombre if curso.ciclo.carrera else None
            }
            
            cursos_response.append(curso_data)
        
        return cursos_response
        
    except Exception as e:
        print(f"Error in get_student_courses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener los cursos del estudiante"
        )

@router.get("/enrollments", response_model=List[MatriculaResponse])
def get_student_enrollments(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db),
    ciclo_id: Optional[int] = Query(None, description="Filtrar por ciclo específico")
):
    """Obtener matrículas del estudiante"""
    
    try:
        # Query base para matrículas del estudiante
        matriculas_query = db.query(Matricula).filter(
            Matricula.estudiante_id == current_user.id
        ).options(
            joinedload(Matricula.ciclo).joinedload(Ciclo.carrera),
            joinedload(Matricula.estudiante)
        )
        
        # Aplicar filtros
        if ciclo_id:
            matriculas_query = matriculas_query.filter(Matricula.ciclo_id == ciclo_id)
        
        matriculas = matriculas_query.order_by(Matricula.created_at.desc()).all()
        
        # Convertir a formato de respuesta
        matriculas_response = []
        for matricula in matriculas:
            matricula_data = {
                "id": matricula.id,
                "estudiante_id": matricula.estudiante_id,
                "estudiante_nombre": f"{matricula.estudiante.first_name} {matricula.estudiante.last_name}",
                "ciclo_id": matricula.ciclo_id,
                "ciclo_nombre": matricula.ciclo.nombre,
                "ciclo_año": matricula.ciclo.año,
                "carrera_nombre": matricula.ciclo.carrera.nombre if matricula.ciclo.carrera else None,
                "fecha_matricula": matricula.created_at,
                "is_active": matricula.is_active
            }
            
            matriculas_response.append(matricula_data)
        
        return matriculas_response
        
    except Exception as e:
        print(f"Error in get_student_enrollments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las matrículas del estudiante"
        )