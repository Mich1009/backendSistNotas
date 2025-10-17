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
    EstudianteDashboard, EstadisticasEstudiante,
    PromedioFinalEstudianteResponse, NotasPorTipoResponse
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
            "docente_nombre": f"{curso.docente.first_name} {curso.docente.last_name}" if curso.docente else "Sin asignar",
            "ciclo_nombre": curso.ciclo.nombre
        }
        cursos_response.append(curso_data)
    
    # Obtener notas recientes
    notas_recientes = db.query(Nota).filter(
        Nota.estudiante_id == current_user.id
    ).options(
        joinedload(Nota.curso).joinedload(Curso.docente)
    ).order_by(Nota.created_at.desc()).limit(10).all()
    
    # Convertir notas a formato de respuesta
    notas_response = []
    for nota in notas_recientes:
        nota_data = {
            "id": nota.id,
            "curso_nombre": nota.curso.nombre,
            "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}" if nota.curso.docente else "Sin asignar",
            "tipo_evaluacion": nota.tipo_evaluacion,
            "valor_nota": float(nota.valor_nota),
            "peso": float(nota.peso),
            "fecha_evaluacion": nota.fecha_evaluacion.strftime("%Y-%m-%d"),
            "observaciones": nota.observaciones,
            "created_at": nota.created_at
        }
        notas_response.append(nota_data)
    
    # Calcular estadísticas
    total_cursos = len(cursos_actuales)
    
    # Calcular promedio general usando GradeCalculator
    from app.shared.grade_calculator import GradeCalculator
    
    promedios_por_curso = []
    cursos_aprobados = 0
    cursos_desaprobados = 0
    
    for curso in cursos_actuales:
        resultado = GradeCalculator.calcular_promedio_final(current_user.id, curso.id, db)
        if resultado["promedio_final"] > 0:
            promedios_por_curso.append(resultado["promedio_final"])
            if resultado["estado"] == "APROBADO":
                cursos_aprobados += 1
            else:
                cursos_desaprobados += 1
    
    promedio_general = None
    if promedios_por_curso:
        promedio_general = sum(promedios_por_curso) / len(promedios_por_curso)
    
    # Calcular créditos completados (sin campo creditos, usar conteo de cursos)
    creditos_completados = len([
        curso for curso in cursos_actuales 
        if any(promedio >= 10.5 for promedio in promedios_por_curso)
    ])
    
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
        
        notas = query.order_by(Nota.created_at.desc()).all()
        
        # Convertir a formato de respuesta
        notas_response = []
        for nota in notas:
            nota_data = {
                "id": nota.id,
                "curso_nombre": nota.curso.nombre,
                "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}" if nota.curso.docente else "Sin asignar",
                "tipo_evaluacion": nota.tipo_evaluacion,
                "valor_nota": float(nota.valor_nota),
                "peso": float(nota.peso),
                "fecha_evaluacion": nota.fecha_evaluacion.strftime("%Y-%m-%d"),
                "observaciones": nota.observaciones,
                "created_at": nota.created_at
            }
            notas_response.append(nota_data)
        
        return notas_response
    except Exception as e:
        print(f"Error in get_student_grades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las notas del estudiante"
        )

@router.get("/grades/{curso_id}", response_model=List[NotaEstudianteResponse])
def get_student_grade_by_course(
    curso_id: int,
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener todas las notas de un curso específico"""
    
    notas = db.query(Nota).filter(
        Nota.estudiante_id == current_user.id,
        Nota.curso_id == curso_id
    ).options(
        joinedload(Nota.curso).joinedload(Curso.docente)
    ).order_by(Nota.fecha_evaluacion.desc()).all()
    
    if not notas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron notas para este curso"
        )
    
    # Convertir a formato de respuesta
    notas_response = []
    for nota in notas:
        nota_data = {
            "id": nota.id,
            "curso_nombre": nota.curso.nombre,
            "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}" if nota.curso.docente else "Sin asignar",
            "tipo_evaluacion": nota.tipo_evaluacion,
            "valor_nota": float(nota.valor_nota),
            "peso": float(nota.peso),
            "fecha_evaluacion": nota.fecha_evaluacion.strftime("%Y-%m-%d"),
            "observaciones": nota.observaciones,
            "created_at": nota.created_at
        }
        notas_response.append(nota_data)
    
    return notas_response

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
    
    # Calcular estadísticas usando GradeCalculator
    from app.shared.grade_calculator import GradeCalculator
    
    promedios_por_curso = []
    cursos_aprobados = 0
    cursos_desaprobados = 0
    
    for curso in cursos_actuales:
        resultado = GradeCalculator.calcular_promedio_final(current_user.id, curso.id, db)
        if resultado["promedio_final"] > 0:
            promedios_por_curso.append(resultado["promedio_final"])
            if resultado["estado"] == "APROBADO":
                cursos_aprobados += 1
            else:
                cursos_desaprobados += 1
    
    # Calcular estadísticas
    total_cursos = len(cursos_actuales)
    
    promedio_general = None
    if promedios_por_curso:
        promedio_general = sum(promedios_por_curso) / len(promedios_por_curso)
    
    # Calcular créditos completados (cursos aprobados)
    creditos_completados = sum(
        curso.creditos for curso in cursos_actuales 
        if any(promedio >= 10.5 for promedio in promedios_por_curso)
    )
    
    return {
        "total_cursos": total_cursos,
        "promedio_general": promedio_general,
        "cursos_aprobados": cursos_aprobados,
        "cursos_desaprobados": cursos_desaprobados,
        "creditos_completados": creditos_completados
    }

# Nuevos endpoints para el sistema de calificaciones mejorado

@router.get("/final-grades", response_model=List[PromedioFinalEstudianteResponse])
def get_student_final_grades(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener promedios finales de todos los cursos del estudiante"""
    
    # Obtener cursos del estudiante
    matriculas_activas = db.query(Matricula).filter(
        Matricula.estudiante_id == current_user.id,
        Matricula.is_active == True
    ).all()
    
    ciclo_ids = [matricula.ciclo_id for matricula in matriculas_activas]
    cursos = db.query(Curso).filter(
        Curso.ciclo_id.in_(ciclo_ids),
        Curso.is_active == True
    ).all()
    
    # Calcular promedios finales usando GradeCalculator
    from app.shared.grade_calculator import GradeCalculator
    
    resultados = []
    for curso in cursos:
        resultado = GradeCalculator.calcular_promedio_final(current_user.id, curso.id, db)
        resultados.append({
            "curso_id": curso.id,
            "curso_nombre": curso.nombre,
            "promedio_final": resultado["promedio_final"],
            "estado": resultado["estado"],
            "detalle": resultado["detalle"]
        })
    
    return resultados

@router.get("/final-grades/{curso_id}", response_model=PromedioFinalEstudianteResponse)
def get_student_final_grade_by_course(
    curso_id: int,
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener promedio final de un curso específico"""
    
    # Verificar que el estudiante está matriculado en el curso
    matricula = db.query(Matricula).filter(
        Matricula.estudiante_id == current_user.id,
        Matricula.curso_id == curso_id,
        Matricula.is_active == True
    ).first()
    
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No estás matriculado en este curso"
        )
    
    # Obtener información del curso
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado"
        )
    
    # Calcular promedio final usando GradeCalculator
    from app.shared.grade_calculator import GradeCalculator
    resultado = GradeCalculator.calcular_promedio_final(current_user.id, curso_id, db)
    
    return {
        "curso_id": curso_id,
        "curso_nombre": curso.nombre,
        "promedio_final": resultado["promedio_final"],
        "estado": resultado["estado"],
        "detalle": resultado["detalle"]
    }

@router.get("/grades-by-type/{curso_id}", response_model=NotasPorTipoResponse)
def get_student_grades_by_type(
    curso_id: int,
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener notas agrupadas por tipo de evaluación para un curso"""
    
    # Verificar que el estudiante está matriculado en el curso
    matricula = db.query(Matricula).filter(
        Matricula.estudiante_id == current_user.id,
        Matricula.curso_id == curso_id,
        Matricula.is_active == True
    ).first()
    
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No estás matriculado en este curso"
        )
    
    # Obtener información del curso
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado"
        )
    
    # Obtener todas las notas del estudiante en este curso
    notas = db.query(Nota).filter(
        Nota.estudiante_id == current_user.id,
        Nota.curso_id == curso_id
    ).options(
        joinedload(Nota.curso).joinedload(Curso.docente)
    ).order_by(Nota.fecha_evaluacion).all()
    
    # Agrupar notas por tipo
    notas_semanales = []
    notas_practicas = []
    notas_parciales = []
    
    for nota in notas:
        nota_data = {
            "id": nota.id,
            "curso_nombre": nota.curso.nombre,
            "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}" if nota.curso.docente else "Sin asignar",
            "tipo_evaluacion": nota.tipo_evaluacion,
            "valor_nota": float(nota.valor_nota),
            "peso": float(nota.peso),
            "fecha_evaluacion": nota.fecha_evaluacion.strftime("%Y-%m-%d"),
            "observaciones": nota.observaciones,
            "created_at": nota.created_at
        }
        
        if nota.tipo_evaluacion == "SEMANAL":
            notas_semanales.append(nota_data)
        elif nota.tipo_evaluacion == "PRACTICA":
            notas_practicas.append(nota_data)
        elif nota.tipo_evaluacion == "PARCIAL":
            notas_parciales.append(nota_data)
    
    # Calcular promedio final
    from app.shared.grade_calculator import GradeCalculator
    resultado = GradeCalculator.calcular_promedio_final(current_user.id, curso_id, db)
    
    return {
        "curso_id": curso_id,
        "curso_nombre": curso.nombre,
        "notas_semanales": notas_semanales,
        "notas_practicas": notas_practicas,
        "notas_parciales": notas_parciales,
        "promedio_final": resultado["promedio_final"],
        "estado": resultado["estado"]
    }