from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from ...database import get_db
from ..auth.dependencies import get_docente_user, get_current_active_user
from ..auth.models import User, RoleEnum
from .models import Carrera, Ciclo, Curso, Matricula, Nota, HistorialNota
from .schemas import (
    CursoDocenteResponse, EstudianteEnCurso, EstudianteConNota,
    NotaCreate, NotaUpdate, NotaDocenteResponse, ActualizacionMasivaNotas,
    DocenteDashboard, EstadisticasDocente, ReporteCurso, EstadisticasCurso,
    CursoDocenteUpdate
)

router = APIRouter(prefix="/teacher", tags=["Docente"])

@router.get("/dashboard", response_model=DocenteDashboard)
def get_teacher_dashboard(
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener dashboard completo del docente"""
    
    # Obtener cursos del docente
    cursos = db.query(Curso).filter(
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).options(
        joinedload(Curso.carrera),
        joinedload(Curso.ciclo)
    ).all()
    
    # Convertir cursos a formato de respuesta
    cursos_response = []
    total_estudiantes = 0
    
    for curso in cursos:
        # Contar estudiantes matriculados
        estudiantes_count = db.query(Matricula).filter(
            Matricula.curso_id == curso.id,
            Matricula.is_active == True
        ).count()
        
        total_estudiantes += estudiantes_count
        
        curso_data = {
            "id": curso.id,
            "nombre": curso.nombre,
            "codigo": curso.codigo,
            "creditos": curso.creditos,
            "horas_semanales": curso.horas_semanales,
            "horario": curso.horario,
            "aula": curso.aula,
            "max_estudiantes": curso.max_estudiantes,
            "carrera_id": curso.carrera_id,
            "ciclo_id": curso.ciclo_id,
            "docente_id": curso.docente_id,
            "is_active": curso.is_active,
            "created_at": curso.created_at,
            "carrera_nombre": curso.carrera.nombre,
            "ciclo_nombre": curso.ciclo.nombre,
            "total_estudiantes": estudiantes_count
        }
        cursos_response.append(curso_data)
    
    # Calcular estadísticas generales
    total_cursos = len(cursos)
    
    # Obtener todas las notas de los cursos del docente
    notas_docente = db.query(Nota).join(Curso).filter(
        Curso.docente_id == current_user.id,
        Nota.promedio.isnot(None)
    ).all()
    
    promedio_general = None
    if notas_docente:
        suma_promedios = sum(float(nota.promedio) for nota in notas_docente)
        promedio_general = Decimal(str(suma_promedios / len(notas_docente)))
    
    estudiantes_aprobados = sum(1 for nota in notas_docente if nota.promedio >= 11)
    estudiantes_desaprobados = sum(1 for nota in notas_docente if nota.promedio < 11)
    
    # Actividad reciente (últimas notas modificadas)
    actividad_reciente = db.query(Nota).join(Curso).filter(
        Curso.docente_id == current_user.id
    ).options(
        joinedload(Nota.estudiante),
        joinedload(Nota.curso)
    ).order_by(Nota.updated_at.desc()).limit(10).all()
    
    actividad_response = []
    for nota in actividad_reciente:
        actividad_data = {
            "tipo": "nota_actualizada",
            "descripcion": f"Nota actualizada para {nota.estudiante.nombres} {nota.estudiante.apellidos} en {nota.curso.nombre}",
            "fecha": nota.updated_at or nota.created_at,
            "curso": nota.curso.nombre,
            "estudiante": f"{nota.estudiante.nombres} {nota.estudiante.apellidos}"
        }
        actividad_response.append(actividad_data)
    
    estadisticas = {
        "total_cursos": total_cursos,
        "total_estudiantes": total_estudiantes,
        "promedio_general_cursos": promedio_general,
        "estudiantes_aprobados": estudiantes_aprobados,
        "estudiantes_desaprobados": estudiantes_desaprobados
    }
    
    return {
        "docente_info": {
            "dni": current_user.dni,
            "nombres": current_user.nombres,
            "apellidos": current_user.apellidos,
            "email": current_user.email
        },
        "cursos_actuales": cursos_response,
        "estadisticas_generales": estadisticas,
        "actividad_reciente": actividad_response
    }

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
        joinedload(Curso.carrera),
        joinedload(Curso.ciclo)
    )
    
    if ciclo_id:
        query = query.filter(Curso.ciclo_id == ciclo_id)
    
    cursos = query.all()
    
    # Convertir a formato de respuesta con información adicional
    cursos_response = []
    for curso in cursos:
        # Contar estudiantes matriculados
        estudiantes_count = db.query(Matricula).filter(
            Matricula.curso_id == curso.id,
            Matricula.is_active == True
        ).count()
        
        curso_data = {
            "id": curso.id,
            "nombre": curso.nombre,
            "codigo": curso.codigo,
            "creditos": curso.creditos,
            "horas_semanales": curso.horas_semanales,
            "horario": curso.horario,
            "aula": curso.aula,
            "max_estudiantes": curso.max_estudiantes,
            "carrera_id": curso.carrera_id,
            "ciclo_id": curso.ciclo_id,
            "docente_id": curso.docente_id,
            "is_active": curso.is_active,
            "created_at": curso.created_at,
            "carrera_nombre": curso.carrera.nombre,
            "ciclo_nombre": curso.ciclo.nombre,
            "total_estudiantes": estudiantes_count
        }
        cursos_response.append(curso_data)
    
    return cursos_response

@router.get("/courses/{curso_id}/students", response_model=List[EstudianteEnCurso])
def get_course_students(
    curso_id: int,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener estudiantes matriculados en un curso del docente"""
    
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
    
    # Obtener estudiantes matriculados
    estudiantes = db.query(User, Matricula.fecha_matricula).join(
        Matricula, User.id == Matricula.estudiante_id
    ).filter(
        Matricula.curso_id == curso_id,
        Matricula.is_active == True,
        User.role == RoleEnum.ESTUDIANTE
    ).order_by(User.apellidos, User.nombres).all()
    
    # Convertir a formato de respuesta
    estudiantes_response = []
    for user, fecha_matricula in estudiantes:
        estudiante_data = {
            "id": user.id,
            "dni": user.dni,
            "nombres": user.nombres,
            "apellidos": user.apellidos,
            "email": user.email,
            "fecha_matricula": fecha_matricula
        }
        estudiantes_response.append(estudiante_data)
    
    return estudiantes_response

@router.get("/courses/{curso_id}/students-with-grades", response_model=List[EstudianteConNota])
def get_course_students_with_grades(
    curso_id: int,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener estudiantes con sus notas en un curso específico"""
    
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
    
    # Obtener estudiantes con sus notas
    estudiantes_con_notas = db.query(
        User, Matricula.fecha_matricula, Nota
    ).join(
        Matricula, User.id == Matricula.estudiante_id
    ).outerjoin(
        Nota, and_(Nota.estudiante_id == User.id, Nota.curso_id == curso_id)
    ).filter(
        Matricula.curso_id == curso_id,
        Matricula.is_active == True,
        User.role == RoleEnum.ESTUDIANTE
    ).order_by(User.apellidos, User.nombres).all()
    
    # Convertir a formato de respuesta
    estudiantes_response = []
    for user, fecha_matricula, nota in estudiantes_con_notas:
        estudiante_data = {
            "id": user.id,
            "dni": user.dni,
            "nombres": user.nombres,
            "apellidos": user.apellidos,
            "email": user.email,
            "fecha_matricula": fecha_matricula,
            "nota_1": nota.nota_1 if nota else None,
            "nota_2": nota.nota_2 if nota else None,
            "nota_3": nota.nota_3 if nota else None,
            "nota_4": nota.nota_4 if nota else None,
            "promedio": nota.promedio if nota else None,
            "observaciones": nota.observaciones if nota else None
        }
        estudiantes_response.append(estudiante_data)
    
    return estudiantes_response

@router.post("/grades", response_model=NotaDocenteResponse)
def create_grade(
    nota_data: NotaCreate,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Crear una nueva nota"""
    
    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == nota_data.curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no tienes permisos para crear notas"
        )
    
    # Verificar que el estudiante está matriculado en el curso
    matricula = db.query(Matricula).filter(
        Matricula.estudiante_id == nota_data.estudiante_id,
        Matricula.curso_id == nota_data.curso_id,
        Matricula.is_active == True
    ).first()
    
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estudiante no está matriculado en este curso"
        )
    
    # Verificar que no existe ya una nota para este estudiante en este curso
    nota_existente = db.query(Nota).filter(
        Nota.estudiante_id == nota_data.estudiante_id,
        Nota.curso_id == nota_data.curso_id
    ).first()
    
    if nota_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una nota para este estudiante en este curso"
        )
    
    # Crear nueva nota
    nueva_nota = Nota(
        estudiante_id=nota_data.estudiante_id,
        curso_id=nota_data.curso_id,
        nota_1=nota_data.nota_1,
        nota_2=nota_data.nota_2,
        nota_3=nota_data.nota_3,
        nota_4=nota_data.nota_4,
        observaciones=nota_data.observaciones,
        created_by=current_user.id
    )
    
    # Calcular promedio
    nueva_nota.promedio = nueva_nota.calcular_promedio()
    
    db.add(nueva_nota)
    db.commit()
    db.refresh(nueva_nota)
    
    # Obtener información del estudiante para la respuesta
    estudiante = db.query(User).filter(User.id == nota_data.estudiante_id).first()
    
    return {
        "id": nueva_nota.id,
        "estudiante_id": nueva_nota.estudiante_id,
        "curso_id": nueva_nota.curso_id,
        "nota_1": nueva_nota.nota_1,
        "nota_2": nueva_nota.nota_2,
        "nota_3": nueva_nota.nota_3,
        "nota_4": nueva_nota.nota_4,
        "promedio": nueva_nota.promedio,
        "observaciones": nueva_nota.observaciones,
        "created_at": nueva_nota.created_at,
        "updated_at": nueva_nota.updated_at,
        "estudiante_dni": estudiante.dni,
        "estudiante_nombres": estudiante.nombres,
        "estudiante_apellidos": estudiante.apellidos
    }

@router.put("/grades/{nota_id}", response_model=NotaDocenteResponse)
def update_grade(
    nota_id: int,
    nota_data: NotaUpdate,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Actualizar una nota existente"""
    
    # Obtener la nota con información del curso
    nota = db.query(Nota).join(Curso).filter(
        Nota.id == nota_id,
        Curso.docente_id == current_user.id
    ).first()
    
    if not nota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota no encontrada o no tienes permisos para modificarla"
        )
    
    # Actualizar campos proporcionados
    if nota_data.nota_1 is not None:
        nota.nota_1 = nota_data.nota_1
    if nota_data.nota_2 is not None:
        nota.nota_2 = nota_data.nota_2
    if nota_data.nota_3 is not None:
        nota.nota_3 = nota_data.nota_3
    if nota_data.nota_4 is not None:
        nota.nota_4 = nota_data.nota_4
    if nota_data.observaciones is not None:
        nota.observaciones = nota_data.observaciones
    
    # Recalcular promedio
    nota.promedio = nota.calcular_promedio()
    nota.updated_by = current_user.id
    
    db.commit()
    db.refresh(nota)
    
    # Obtener información del estudiante para la respuesta
    estudiante = db.query(User).filter(User.id == nota.estudiante_id).first()
    
    return {
        "id": nota.id,
        "estudiante_id": nota.estudiante_id,
        "curso_id": nota.curso_id,
        "nota_1": nota.nota_1,
        "nota_2": nota.nota_2,
        "nota_3": nota.nota_3,
        "nota_4": nota.nota_4,
        "promedio": nota.promedio,
        "observaciones": nota.observaciones,
        "created_at": nota.created_at,
        "updated_at": nota.updated_at,
        "estudiante_dni": estudiante.dni,
        "estudiante_nombres": estudiante.nombres,
        "estudiante_apellidos": estudiante.apellidos
    }

@router.put("/courses/{curso_id}", response_model=CursoDocenteResponse)
def update_course(
    curso_id: int,
    curso_data: CursoDocenteUpdate,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Actualizar información del curso (solo campos permitidos para el docente)"""
    
    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no tienes permisos para modificarlo"
        )
    
    # Actualizar campos permitidos
    if curso_data.nombre is not None:
        curso.nombre = curso_data.nombre
    if curso_data.horario is not None:
        curso.horario = curso_data.horario
    if curso_data.aula is not None:
        curso.aula = curso_data.aula
    if curso_data.max_estudiantes is not None:
        curso.max_estudiantes = curso_data.max_estudiantes
    
    db.commit()
    db.refresh(curso)
    
    # Obtener información adicional para la respuesta
    carrera = db.query(Carrera).filter(Carrera.id == curso.carrera_id).first()
    ciclo = db.query(Ciclo).filter(Ciclo.id == curso.ciclo_id).first()
    
    estudiantes_count = db.query(Matricula).filter(
        Matricula.curso_id == curso.id,
        Matricula.is_active == True
    ).count()
    
    return {
        "id": curso.id,
        "nombre": curso.nombre,
        "codigo": curso.codigo,
        "creditos": curso.creditos,
        "horas_semanales": curso.horas_semanales,
        "horario": curso.horario,
        "aula": curso.aula,
        "max_estudiantes": curso.max_estudiantes,
        "carrera_id": curso.carrera_id,
        "ciclo_id": curso.ciclo_id,
        "docente_id": curso.docente_id,
        "is_active": curso.is_active,
        "created_at": curso.created_at,
        "carrera_nombre": carrera.nombre if carrera else None,
        "ciclo_nombre": ciclo.nombre if ciclo else None,
        "total_estudiantes": estudiantes_count
    }

@router.get("/courses/{curso_id}/statistics", response_model=EstadisticasCurso)
def get_course_statistics(
    curso_id: int,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener estadísticas detalladas de un curso"""
    
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
    
    # Contar estudiantes matriculados
    total_estudiantes = db.query(Matricula).filter(
        Matricula.curso_id == curso_id,
        Matricula.is_active == True
    ).count()
    
    # Obtener todas las notas del curso
    notas = db.query(Nota).filter(
        Nota.curso_id == curso_id,
        Nota.promedio.isnot(None)
    ).all()
    
    # Calcular estadísticas
    promedio_curso = None
    if notas:
        suma_promedios = sum(float(nota.promedio) for nota in notas)
        promedio_curso = Decimal(str(suma_promedios / len(notas)))
    
    estudiantes_aprobados = sum(1 for nota in notas if nota.promedio >= 11)
    estudiantes_desaprobados = sum(1 for nota in notas if nota.promedio < 11)
    estudiantes_sin_notas = total_estudiantes - len(notas)
    
    # Distribución de notas por rangos
    distribucion = {
        "0-5": sum(1 for nota in notas if 0 <= nota.promedio < 6),
        "6-10": sum(1 for nota in notas if 6 <= nota.promedio < 11),
        "11-15": sum(1 for nota in notas if 11 <= nota.promedio < 16),
        "16-20": sum(1 for nota in notas if 16 <= nota.promedio <= 20)
    }
    
    return {
        "total_estudiantes": total_estudiantes,
        "promedio_curso": promedio_curso,
        "estudiantes_aprobados": estudiantes_aprobados,
        "estudiantes_desaprobados": estudiantes_desaprobados,
        "estudiantes_sin_notas": estudiantes_sin_notas,
        "distribucion_notas": distribucion
    }

@router.post("/grades/bulk-update")
def bulk_update_grades(
    actualizacion: ActualizacionMasivaNotas,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Actualización masiva de notas"""
    
    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == actualizacion.curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no tienes permisos para modificar notas"
        )
    
    actualizaciones_exitosas = []
    errores = []
    
    for nota_data in actualizacion.notas:
        try:
            # Buscar o crear nota
            nota = db.query(Nota).filter(
                Nota.estudiante_id == nota_data.estudiante_id,
                Nota.curso_id == actualizacion.curso_id
            ).first()
            
            if not nota:
                # Verificar que el estudiante está matriculado
                matricula = db.query(Matricula).filter(
                    Matricula.estudiante_id == nota_data.estudiante_id,
                    Matricula.curso_id == actualizacion.curso_id,
                    Matricula.is_active == True
                ).first()
                
                if not matricula:
                    errores.append(f"Estudiante {nota_data.estudiante_id} no está matriculado")
                    continue
                
                # Crear nueva nota
                nota = Nota(
                    estudiante_id=nota_data.estudiante_id,
                    curso_id=actualizacion.curso_id,
                    created_by=current_user.id
                )
                db.add(nota)
            
            # Actualizar campos
            if nota_data.nota_1 is not None:
                nota.nota_1 = nota_data.nota_1
            if nota_data.nota_2 is not None:
                nota.nota_2 = nota_data.nota_2
            if nota_data.nota_3 is not None:
                nota.nota_3 = nota_data.nota_3
            if nota_data.nota_4 is not None:
                nota.nota_4 = nota_data.nota_4
            if nota_data.observaciones is not None:
                nota.observaciones = nota_data.observaciones
            
            # Recalcular promedio
            nota.promedio = nota.calcular_promedio()
            nota.updated_by = current_user.id
            
            actualizaciones_exitosas.append(nota_data.estudiante_id)
            
        except Exception as e:
            errores.append(f"Error con estudiante {nota_data.estudiante_id}: {str(e)}")
    
    if actualizaciones_exitosas:
        db.commit()
    
    return {
        "message": "Actualización masiva procesada",
        "actualizaciones_exitosas": len(actualizaciones_exitosas),
        "errores": len(errores),
        "detalles_errores": errores
    }