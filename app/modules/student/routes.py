from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from ...database import get_db
from ..auth.dependencies import get_estudiante_user, get_current_active_user
from ..auth.models import User, RoleEnum
from .models import Carrera, Ciclo, Curso, Matricula, Nota
from .schemas import (
    CarreraResponse, CicloResponse, CursoEstudianteResponse, 
    MatriculaResponse, NotaEstudianteResponse,
    EstudianteDashboard, EstadisticasEstudiante
)

router = APIRouter(prefix="/student", tags=["Estudiante"])

@router.get("/dashboard", response_model=EstudianteDashboard)
def get_student_dashboard(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener dashboard completo del estudiante"""
    
    # Obtener cursos actuales del estudiante a través de matrículas
    matriculas_activas = db.query(Matricula).filter(
        Matricula.estudiante_id == current_user.id,
        Matricula.is_active == True
    ).all()
    
    # Obtener cursos de los ciclos en los que está matriculado
    ciclo_ids = [matricula.ciclo_id for matricula in matriculas_activas]
    cursos_actuales = db.query(Curso).filter(
        Curso.ciclo_id.in_(ciclo_ids),
        Curso.is_active == True
    ).options(
        joinedload(Curso.ciclo).joinedload(Ciclo.carrera),
        joinedload(Curso.docente)
    ).all()
    
    # Convertir a formato de respuesta
    cursos_response = []
    for curso in cursos_actuales:
        curso_data = {
            "id": curso.id,
            "nombre": curso.nombre,
            "codigo": curso.codigo,
            "creditos": curso.creditos,
            "horas_semanales": getattr(curso, 'horas_semanales', 0),
            "docente_nombre": f"{curso.docente.first_name} {curso.docente.last_name}" if curso.docente else "Sin asignar",
            "ciclo_nombre": curso.ciclo.nombre
        }
        cursos_response.append(curso_data)
    
    # Obtener notas recientes
    notas_recientes = db.query(Nota).filter(
        Nota.estudiante_id == current_user.id
    ).options(
        joinedload(Nota.curso).joinedload(Curso.docente)
    ).order_by(Nota.updated_at.desc()).limit(10).all()
    
    # Convertir notas a formato de respuesta
    notas_response = []
    for nota in notas_recientes:
        nota_data = {
            "id": nota.id,
            "curso_nombre": nota.curso.nombre,
            "curso_codigo": nota.curso.codigo,
            "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}" if nota.curso.docente else "Sin asignar",
            "nota_1": None,  # El modelo actual no tiene estos campos
            "nota_2": None,
            "nota_3": None,
            "nota_4": None,
            "promedio": float(nota.nota) if nota.nota else None,
            "observaciones": nota.observaciones
        }
        notas_response.append(nota_data)
    
    # Calcular estadísticas
    total_cursos = len(cursos_actuales)
    
    # Calcular promedio general
    todas_las_notas = db.query(Nota).filter(
        Nota.estudiante_id == current_user.id,
        Nota.nota.isnot(None)
    ).all()
    
    promedio_general = None
    if todas_las_notas:
        suma_promedios = sum(float(nota.nota) for nota in todas_las_notas)
        promedio_general = Decimal(str(suma_promedios / len(todas_las_notas)))
    
    # Contar cursos aprobados/desaprobados
    cursos_aprobados = sum(1 for nota in todas_las_notas if nota.nota and float(nota.nota) >= 11)
    cursos_desaprobados = sum(1 for nota in todas_las_notas if nota.nota and float(nota.nota) < 11)
    
    # Calcular créditos completados
    creditos_completados = sum(
        curso.creditos for curso in cursos_actuales 
        if any(nota.nota and float(nota.nota) >= 11 for nota in todas_las_notas if nota.curso_id == curso.id)
    )
    
    estadisticas = {
        "total_cursos": total_cursos,
        "promedio_general": promedio_general,
        "cursos_aprobados": cursos_aprobados,
        "cursos_desaprobados": cursos_desaprobados,
        "creditos_completados": creditos_completados
    }
    
    return {
        "estudiante_info": {
            "dni": current_user.dni,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email
        },
        "cursos_actuales": cursos_response,
        "notas_recientes": notas_response,
        "estadisticas": estadisticas
    }

@router.get("/courses", response_model=List[CursoEstudianteResponse])
def get_student_courses(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db),
    ciclo_id: Optional[int] = Query(None, description="Filtrar por ciclo específico")
):
    """Obtener cursos del estudiante"""
    
    try:
        # Obtener matrículas activas del estudiante
        matriculas_activas = db.query(Matricula).filter(
            Matricula.estudiante_id == current_user.id,
            Matricula.is_active == True
        )
        
        if ciclo_id:
            matriculas_activas = matriculas_activas.filter(Matricula.ciclo_id == ciclo_id)
        
        matriculas_activas = matriculas_activas.all()
        
        # Obtener cursos de los ciclos en los que está matriculado
        ciclo_ids = [matricula.ciclo_id for matricula in matriculas_activas]
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
                "codigo": curso.codigo,
                "creditos": curso.creditos,
                "horas_semanales": getattr(curso, 'horas_semanales', 0),
                "horario": getattr(curso, 'horario', None),
                "aula": getattr(curso, 'aula', None),
                "docente_nombre": f"{curso.docente.first_name} {curso.docente.last_name}" if curso.docente else "Sin asignar",
                "carrera_nombre": curso.ciclo.carrera.nombre if curso.ciclo and curso.ciclo.carrera else "Sin carrera",
                "ciclo_nombre": curso.ciclo.nombre
            }
            cursos_response.append(curso_data)
        
        return cursos_response
    except Exception as e:
        print(f"Error in get_student_courses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener los cursos del estudiante"
        )

@router.get("/grades", response_model=List[NotaEstudianteResponse])
def get_student_grades(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db),
    curso_id: Optional[int] = Query(None, description="Filtrar por curso específico")
):
    """Obtener notas del estudiante"""
    
    try:
        query = db.query(Nota).filter(
            Nota.estudiante_id == current_user.id
        ).options(
            joinedload(Nota.curso).joinedload(Curso.docente)
        )
        
        if curso_id:
            query = query.filter(Nota.curso_id == curso_id)
        
        notas = query.order_by(Nota.updated_at.desc()).all()
        
        # Convertir a formato de respuesta
        notas_response = []
        for nota in notas:
            nota_data = {
                "id": nota.id,
                "curso_nombre": nota.curso.nombre,
                "curso_codigo": nota.curso.codigo,
                "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}" if nota.curso.docente else "Sin asignar",
                "nota_1": None,  # El modelo actual no tiene estos campos
                "nota_2": None,
                "nota_3": None,
                "nota_4": None,
                "promedio": float(nota.nota) if nota.nota else None,
                "observaciones": nota.observaciones
            }
            notas_response.append(nota_data)
        
        return notas_response
    except Exception as e:
        print(f"Error in get_student_grades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las notas del estudiante"
        )

@router.get("/grades/{curso_id}", response_model=NotaEstudianteResponse)
def get_student_grade_by_course(
    curso_id: int,
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener nota específica de un curso"""
    
    nota = db.query(Nota).filter(
        Nota.estudiante_id == current_user.id,
        Nota.curso_id == curso_id
    ).options(
        joinedload(Nota.curso).joinedload(Curso.docente)
    ).first()
    
    if not nota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota no encontrada para este curso"
        )
    
    return {
        "id": nota.id,
        "curso_nombre": nota.curso.nombre,
        "curso_codigo": nota.curso.codigo,
        "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}" if nota.curso.docente else "Sin asignar",
        "nota_1": None,  # El modelo actual no tiene estos campos
        "nota_2": None,
        "nota_3": None,
        "nota_4": None,
        "promedio": float(nota.nota) if nota.nota else None,
        "observaciones": nota.observaciones
    }

@router.get("/enrollments", response_model=List[MatriculaResponse])
def get_student_enrollments(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener matrículas del estudiante"""
    
    matriculas = db.query(Matricula).filter(
        Matricula.estudiante_id == current_user.id
    ).options(
        joinedload(Matricula.curso),
        joinedload(Matricula.ciclo)
    ).order_by(Matricula.fecha_matricula.desc()).all()
    
    return matriculas

# Endpoint de cursos disponibles eliminado - los estudiantes solo tienen permisos de lectura

# Endpoint de matrícula eliminado - los estudiantes solo tienen permisos de lectura
# La matrícula debe ser gestionada por el administrador

@router.get("/statistics", response_model=EstadisticasEstudiante)
def get_student_statistics(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener estadísticas del estudiante"""
    
    # Obtener todas las notas del estudiante
    notas = db.query(Nota).filter(
        Nota.estudiante_id == current_user.id,
        Nota.nota.isnot(None)
    ).all()
    
    # Obtener cursos actuales a través de matrículas
    matriculas_activas = db.query(Matricula).filter(
        Matricula.estudiante_id == current_user.id,
        Matricula.is_active == True
    ).all()
    
    ciclo_ids = [matricula.ciclo_id for matricula in matriculas_activas]
    cursos_actuales = db.query(Curso).filter(
        Curso.ciclo_id.in_(ciclo_ids),
        Curso.is_active == True
    ).all()
    
    # Calcular estadísticas
    total_cursos = len(cursos_actuales)
    
    promedio_general = None
    if notas:
        suma_promedios = sum(float(nota.nota) for nota in notas)
        promedio_general = Decimal(str(suma_promedios / len(notas)))
    
    cursos_aprobados = sum(1 for nota in notas if nota.nota and float(nota.nota) >= 11)
    cursos_desaprobados = sum(1 for nota in notas if nota.nota and float(nota.nota) < 11)
    
    # Calcular créditos completados (cursos aprobados)
    cursos_aprobados_ids = [nota.curso_id for nota in notas if nota.nota and float(nota.nota) >= 11]
    creditos_completados = sum(
        curso.creditos for curso in cursos_actuales 
        if curso.id in cursos_aprobados_ids
    )
    
    return {
        "total_cursos": total_cursos,
        "promedio_general": promedio_general,
        "cursos_aprobados": cursos_aprobados,
        "cursos_desaprobados": cursos_desaprobados,
        "creditos_completados": creditos_completados
    }