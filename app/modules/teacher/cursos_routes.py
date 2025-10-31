from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from ...database import get_db
from ..auth.dependencies import get_docente_user
from ..auth.models import User, RoleEnum
from .models import Carrera, Ciclo, Curso, Matricula, Nota
from ...shared.grade_calculator import GradeCalculator
from .schemas import (
    CursoDocenteResponse, EstudianteEnCurso, EstudianteConNota,
    CicloResponse
)

router = APIRouter()

@router.get("/ciclos", response_model=List[CicloResponse])
def get_teacher_ciclos(
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener ciclos donde el docente tiene cursos asignados"""
    
    # Obtener ciclos únicos donde el docente tiene cursos
    ciclos = db.query(Ciclo).join(Curso).filter(
        Curso.docente_id == current_user.id,
        Curso.is_active == True,
        Ciclo.is_active == True
    ).distinct().options(
        joinedload(Ciclo.carrera)
    ).all()
    
    return ciclos

@router.get("/courses", response_model=List[CursoDocenteResponse])
def get_teacher_courses(
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db),
    ciclo_id: Optional[int] = Query(None, description="Filtrar por ciclo específico")
):
    """Obtener cursos del docente"""
    
    query = db.query(Curso).filter(
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).options(
        joinedload(Curso.ciclo),
        joinedload(Curso.docente)
    )
    
    if ciclo_id:
        query = query.filter(Curso.ciclo_id == ciclo_id)
    
    cursos = query.all()
    
    # Convertir a formato de respuesta con información adicional
    cursos_response = []
    for curso in cursos:
        # Contar estudiantes matriculados en el ciclo del curso
        estudiantes_count = db.query(Matricula).filter(
            Matricula.ciclo_id == curso.ciclo_id,
            Matricula.is_active == True
        ).count()
        
        curso_data = {
            "id": curso.id,
            "nombre": curso.nombre,
            "ciclo_id": curso.ciclo_id,
            "docente_id": curso.docente_id,
            "is_active": curso.is_active,
            "created_at": curso.created_at,
            "ciclo_nombre": curso.ciclo.nombre,
            "fecha_inicio": curso.ciclo.fecha_inicio,
            "fecha_fin": curso.ciclo.fecha_fin,
            "ciclo_año": curso.ciclo.año,
            "total_estudiantes": estudiantes_count
        }
        cursos_response.append(curso_data)
    
    return cursos_response

@router.get("/courses/{curso_id}", response_model=CursoDocenteResponse)
def get_teacher_course(
    curso_id: int,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener un curso específico del docente"""
    
    curso = db.query(Curso).filter(
        Curso.id == curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).options(
        joinedload(Curso.ciclo)
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no tienes permisos para acceder"
        )
    
    # Contar estudiantes matriculados en el ciclo del curso
    estudiantes_count = db.query(Matricula).filter(
        Matricula.ciclo_id == curso.ciclo_id,
        Matricula.is_active == True
    ).count()
    
    return {
        "id": curso.id,
        "nombre": curso.nombre,
        "ciclo_id": curso.ciclo_id,
        "docente_id": curso.docente_id,
        "is_active": curso.is_active,
        "created_at": curso.created_at,
        "ciclo_nombre": curso.ciclo.nombre,
        "total_estudiantes": estudiantes_count
    }

@router.get("/courses/{curso_id}/students", response_model=List[EstudianteEnCurso])
def get_course_students(
    curso_id: int,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener estudiantes matriculados en el ciclo del curso"""

    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no tienes permisos para acceder"
        )
    
    # Obtener estudiantes matriculados en el ciclo del curso
    estudiantes = db.query(
        User, Matricula.fecha_matricula
    ).join(
        Matricula, User.id == Matricula.estudiante_id
    ).filter(
        Matricula.ciclo_id == curso.ciclo_id,
        Matricula.is_active == True,
        User.role == RoleEnum.ESTUDIANTE
    ).all()
    
    # Convertir a formato de respuesta
    estudiantes_response = []
    for user, fecha_matricula in estudiantes:
        estudiantes_response.append({
            "id": user.id,
            "dni": user.dni,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "fecha_matricula": fecha_matricula,
            "phone": user.phone
        })
    
    return estudiantes_response

@router.get("/courses/{curso_id}/students-with-grades", response_model=List[EstudianteConNota])
def get_course_students_with_grades(
    curso_id: int,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """
    Obtener estudiantes con todas sus notas en un curso específico - MEJORADO
    """
    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no tienes permisos para acceder"
        )
    
    # Obtener estudiantes matriculados en el ciclo del curso
    estudiantes = db.query(User).join(
        Matricula, User.id == Matricula.estudiante_id
    ).filter(
        Matricula.ciclo_id == curso.ciclo_id,
        Matricula.is_active == True,
        User.role == RoleEnum.ESTUDIANTE
    ).order_by(User.last_name, User.first_name).all()
    
    # Obtener matrículas para las fechas
    matriculas = db.query(Matricula).filter(
        Matricula.ciclo_id == curso.ciclo_id,
        Matricula.is_active == True
    ).all()
    
    matricula_dict = {m.estudiante_id: m.fecha_matricula for m in matriculas}
    
    # Convertir a formato de respuesta
    estudiantes_response = []
    for estudiante in estudiantes:
        # Obtener la nota consolidada del estudiante en este curso (solo una por estudiante-curso)
        nota = db.query(Nota).filter(
            Nota.estudiante_id == estudiante.id,
            Nota.curso_id == curso_id
        ).first()
        
        # Convertir nota a formato mejorado
        notas_data = []
        if nota:
            nota_dict = {
                "id": nota.id,
                "fecha_evaluacion": nota.fecha_registro.isoformat() if nota.fecha_registro else None,
                "observaciones": nota.observaciones,
                "created_at": nota.created_at,
                # Usar métodos de GradeCalculator para calcular promedios y estado
                "promedio_evaluaciones": GradeCalculator.calcular_promedio_evaluaciones(nota),
                "promedio_practicas": GradeCalculator.calcular_promedio_practicas(nota),
                "promedio_parciales": GradeCalculator.calcular_promedio_parciales(nota),
                "promedio_final": nota.calcular_promedio_final(),
                "estado": nota.obtener_estado()
            }
            
            # Agregar todas las evaluaciones, prácticas y parciales
            for i in range(1, 9):
                eval_key = f"evaluacion{i}"
                eval_val = getattr(nota, eval_key)
                if eval_val is not None:
                    nota_dict[eval_key] = float(eval_val)
            
            for i in range(1, 5):
                prac_key = f"practica{i}"
                prac_val = getattr(nota, prac_key)
                if prac_val is not None:
                    nota_dict[prac_key] = float(prac_val)
            
            for i in range(1, 3):
                par_key = f"parcial{i}"
                par_val = getattr(nota, par_key)
                if par_val is not None:
                    nota_dict[par_key] = float(par_val)
            
            notas_data.append(nota_dict)
        
        estudiante_data = {
            "id": estudiante.id,
            "dni": estudiante.dni,
            "first_name": estudiante.first_name,
            "last_name": estudiante.last_name,
            "email": estudiante.email,
            "fecha_matricula": matricula_dict.get(estudiante.id),
            "notas": notas_data
        }
        estudiantes_response.append(estudiante_data)
    
    return estudiantes_response