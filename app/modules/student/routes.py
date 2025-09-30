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
    MatriculaCreate, MatriculaResponse, NotaEstudianteResponse,
    EstudianteDashboard, EstadisticasEstudiante, SolicitudMatricula
)

router = APIRouter(prefix="/student", tags=["Estudiante"])

@router.get("/dashboard", response_model=EstudianteDashboard)
def get_student_dashboard(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener dashboard completo del estudiante"""
    
    # Obtener cursos actuales del estudiante
    cursos_actuales = db.query(Curso).join(Matricula).filter(
        Matricula.estudiante_id == current_user.id,
        Matricula.is_active == True,
        Curso.is_active == True
    ).options(
        joinedload(Curso.carrera),
        joinedload(Curso.ciclo),
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
            "horas_semanales": curso.horas_semanales,
            "docente_nombre": f"{curso.docente.first_name} {curso.docente.last_name}",
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
            "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}",
            "nota_1": nota.nota_1,
            "nota_2": nota.nota_2,
            "nota_3": nota.nota_3,
            "nota_4": nota.nota_4,
            "promedio": nota.promedio,
            "observaciones": nota.observaciones
        }
        notas_response.append(nota_data)
    
    # Calcular estadísticas
    total_cursos = len(cursos_actuales)
    
    # Calcular promedio general
    todas_las_notas = db.query(Nota).filter(
        Nota.estudiante_id == current_user.id,
        Nota.promedio.isnot(None)
    ).all()
    
    promedio_general = None
    if todas_las_notas:
        suma_promedios = sum(float(nota.promedio) for nota in todas_las_notas)
        promedio_general = Decimal(str(suma_promedios / len(todas_las_notas)))
    
    # Contar cursos aprobados/desaprobados
    cursos_aprobados = sum(1 for nota in todas_las_notas if nota.promedio and nota.promedio >= 11)
    cursos_desaprobados = sum(1 for nota in todas_las_notas if nota.promedio and nota.promedio < 11)
    
    # Calcular créditos completados
    creditos_completados = sum(
        curso.creditos for curso in cursos_actuales 
        if any(nota.promedio and nota.promedio >= 11 for nota in todas_las_notas if nota.curso_id == curso.id)
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
    
    query = db.query(Curso).join(Matricula).filter(
        Matricula.estudiante_id == current_user.id,
        Matricula.is_active == True
    ).options(
        joinedload(Curso.carrera),
        joinedload(Curso.ciclo),
        joinedload(Curso.docente)
    )
    
    if ciclo_id:
        query = query.filter(Curso.ciclo_id == ciclo_id)
    
    cursos = query.all()
    
    # Convertir a formato de respuesta
    cursos_response = []
    for curso in cursos:
        curso_data = {
            "id": curso.id,
            "nombre": curso.nombre,
            "codigo": curso.codigo,
            "creditos": curso.creditos,
            "horas_semanales": curso.horas_semanales,
            "horario": curso.horario,
            "aula": curso.aula,
            "docente_nombre": f"{curso.docente.first_name} {curso.docente.last_name}",
            "carrera_nombre": curso.carrera.nombre,
            "ciclo_nombre": curso.ciclo.nombre
        }
        cursos_response.append(curso_data)
    
    return cursos_response

@router.get("/grades", response_model=List[NotaEstudianteResponse])
def get_student_grades(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db),
    curso_id: Optional[int] = Query(None, description="Filtrar por curso específico")
):
    """Obtener notas del estudiante"""
    
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
            "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}",
            "nota_1": nota.nota_1,
            "nota_2": nota.nota_2,
            "nota_3": nota.nota_3,
            "nota_4": nota.nota_4,
            "promedio": nota.promedio,
            "observaciones": nota.observaciones
        }
        notas_response.append(nota_data)
    
    return notas_response

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
        "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}",
        "nota_1": nota.nota_1,
        "nota_2": nota.nota_2,
        "nota_3": nota.nota_3,
        "nota_4": nota.nota_4,
        "promedio": nota.promedio,
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

@router.get("/available-courses", response_model=List[CursoEstudianteResponse])
def get_available_courses_for_enrollment(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db),
    ciclo_id: Optional[int] = Query(None, description="Filtrar por ciclo específico")
):
    """Obtener cursos disponibles para matrícula"""
    
    # Obtener cursos en los que el estudiante NO está matriculado
    cursos_matriculados = db.query(Matricula.curso_id).filter(
        Matricula.estudiante_id == current_user.id,
        Matricula.is_active == True
    ).subquery()
    
    query = db.query(Curso).filter(
        Curso.is_active == True,
        ~Curso.id.in_(cursos_matriculados)
    ).options(
        joinedload(Curso.carrera),
        joinedload(Curso.ciclo),
        joinedload(Curso.docente)
    )
    
    if ciclo_id:
        query = query.filter(Curso.ciclo_id == ciclo_id)
    
    cursos_disponibles = query.all()
    
    # Convertir a formato de respuesta
    cursos_response = []
    for curso in cursos_disponibles:
        # Verificar cupos disponibles (eliminado - no hay max_estudiantes)
        curso_data = {
            "id": curso.id,
            "nombre": curso.nombre,
            "codigo": curso.codigo,
            "creditos": curso.creditos,
            "horas_semanales": curso.horas_semanales,
            "docente_nombre": f"{curso.docente.first_name} {curso.docente.last_name}",
            "ciclo_nombre": curso.ciclo.nombre
        }
        cursos_response.append(curso_data)
    
    return cursos_response

@router.post("/enroll", response_model=dict)
def enroll_in_courses(
    solicitud: SolicitudMatricula,
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Matricularse en cursos"""
    
    # Verificar que el ciclo existe y está activo
    ciclo = db.query(Ciclo).filter(
        Ciclo.id == solicitud.ciclo_id,
        Ciclo.is_active == True
    ).first()
    
    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado o inactivo"
        )
    
    matriculas_creadas = []
    errores = []
    
    for curso_id in solicitud.cursos_ids:
        # Verificar que el curso existe
        curso = db.query(Curso).filter(
            Curso.id == curso_id,
            Curso.is_active == True,
            Curso.ciclo_id == solicitud.ciclo_id
        ).first()
        
        if not curso:
            errores.append(f"Curso con ID {curso_id} no encontrado o no pertenece al ciclo")
            continue
        
        # Verificar que no esté ya matriculado
        matricula_existente = db.query(Matricula).filter(
            Matricula.estudiante_id == current_user.id,
            Matricula.curso_id == curso_id,
            Matricula.is_active == True
        ).first()
        
        if matricula_existente:
            errores.append(f"Ya está matriculado en el curso {curso.nombre}")
            continue
        
        # Verificar cupos disponibles (eliminado - no hay límite de estudiantes)
        # Crear matrícula
        nueva_matricula = Matricula(
            estudiante_id=current_user.id,
            curso_id=curso_id,
            ciclo_id=solicitud.ciclo_id
        )
        
        db.add(nueva_matricula)
        matriculas_creadas.append(curso.nombre)
    
    if matriculas_creadas:
        db.commit()
    
    return {
        "message": f"Matrícula procesada",
        "cursos_matriculados": matriculas_creadas,
        "errores": errores,
        "total_exitosas": len(matriculas_creadas),
        "total_errores": len(errores)
    }

@router.get("/statistics", response_model=EstadisticasEstudiante)
def get_student_statistics(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener estadísticas del estudiante"""
    
    # Obtener todas las notas del estudiante
    notas = db.query(Nota).filter(
        Nota.estudiante_id == current_user.id,
        Nota.promedio.isnot(None)
    ).all()
    
    # Obtener cursos actuales
    cursos_actuales = db.query(Curso).join(Matricula).filter(
        Matricula.estudiante_id == current_user.id,
        Matricula.is_active == True
    ).all()
    
    # Calcular estadísticas
    total_cursos = len(cursos_actuales)
    
    promedio_general = None
    if notas:
        suma_promedios = sum(float(nota.promedio) for nota in notas)
        promedio_general = Decimal(str(suma_promedios / len(notas)))
    
    cursos_aprobados = sum(1 for nota in notas if nota.promedio >= 11)
    cursos_desaprobados = sum(1 for nota in notas if nota.promedio < 11)
    
    # Calcular créditos completados (cursos aprobados)
    cursos_aprobados_ids = [nota.curso_id for nota in notas if nota.promedio >= 11]
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