from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from ...database import get_db
from ..auth.dependencies import get_docente_user, get_current_active_user
from ..auth.models import User, RoleEnum
from ..auth.security import verify_password, get_password_hash
from .models import Carrera, Ciclo, Curso, Matricula, Nota, HistorialNota
from .schemas import (
    CursoDocenteResponse, EstudianteEnCurso, EstudianteConNota,
    NotaCreate, NotaUpdate, NotaDocenteResponse, ActualizacionMasivaNotas,
    DocenteDashboard, EstadisticasDocente, ReporteCurso, EstadisticasCurso,
    CursoDocenteUpdate, DocenteProfileUpdate, PasswordUpdate, NotaResponse,
    PromedioFinalResponse, EstructuraNotasResponse
)

router = APIRouter(prefix="/teacher", tags=["Docente"])

# Rutas de perfil de docente
@router.get("/profile")
def get_teacher_profile(
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener perfil del docente"""
    return {
        "id": current_user.id,
        "dni": current_user.dni,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "especialidad": current_user.especialidad,
        "grado_academico": current_user.grado_academico,
        "fecha_ingreso": current_user.fecha_ingreso,
        "is_active": current_user.is_active,
        "role": current_user.role
    }

@router.put("/profile")
def update_teacher_profile(
    profile_data: DocenteProfileUpdate,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Actualizar perfil del docente"""
    # Actualizar campos permitidos
    if profile_data.first_name is not None:
        current_user.first_name = profile_data.first_name
    if profile_data.last_name is not None:
        current_user.last_name = profile_data.last_name
    if profile_data.phone is not None:
        current_user.phone = profile_data.phone
    if profile_data.especialidad is not None:
        current_user.especialidad = profile_data.especialidad
    if profile_data.grado_academico is not None:
        current_user.grado_academico = profile_data.grado_academico
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Perfil actualizado correctamente",
        "user": {
            "id": current_user.id,
            "dni": current_user.dni,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "especialidad": current_user.especialidad,
            "grado_academico": current_user.grado_academico,
            "fecha_ingreso": current_user.fecha_ingreso,
            "is_active": current_user.is_active,
            "role": current_user.role
        }
    }

@router.put("/profile/password")
def update_teacher_password(
    password_data: PasswordUpdate,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Actualizar contraseña del docente"""
    # Verificar contraseña actual
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta"
        )
    
    # Actualizar contraseña
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Contraseña actualizada correctamente"}

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
        # Contar estudiantes matriculados en el ciclo del curso
        estudiantes_count = db.query(Matricula).filter(
            Matricula.ciclo_id == curso.ciclo_id,
            Matricula.is_active == True
        ).count()
        
        total_estudiantes += estudiantes_count
        
        curso_data = {
            "id": curso.id,
            "nombre": curso.nombre,
            "ciclo_id": curso.ciclo_id,
            "docente_id": curso.docente_id,
            "is_active": curso.is_active,
            "created_at": curso.created_at,
            "ciclo_nombre": curso.ciclo.nombre,
            "ciclo_año": curso.ciclo.año,
            "total_estudiantes": estudiantes_count
        }
        cursos_response.append(curso_data)
    
    # Calcular estadísticas generales
    total_cursos = len(cursos)
    
    # Obtener promedio general de notas en los cursos del docente
    promedio_general = 0
    estudiantes_aprobados = 0
    estudiantes_desaprobados = 0
    
    if total_cursos > 0:
        # Obtener todas las notas de los cursos del docente
        notas_query = db.query(Nota).filter(
            Nota.curso_id.in_([curso.id for curso in cursos])
        ).all()
        
        total_notas = len(notas_query)
        
        if total_notas > 0:
            # Calcular promedio general
            suma_notas = sum(nota.nota_final for nota in notas_query if nota.nota_final is not None)
            promedio_general = round(suma_notas / total_notas, 2) if total_notas > 0 else 0
            
            # Contar aprobados y desaprobados
            for nota in notas_query:
                if nota.nota_final is not None:
                    if nota.nota_final >= Decimal('10.5'):
                        estudiantes_aprobados += 1
                    else:
                        estudiantes_desaprobados += 1
    
    # Obtener actividad reciente (últimas modificaciones de notas)
    actividad_reciente = db.query(HistorialNota).filter(
        HistorialNota.curso_id.in_([curso.id for curso in cursos])
    ).order_by(HistorialNota.created_at.desc()).limit(5).all()
    
    # Convertir actividad a formato de respuesta
    actividad_response = []
    for actividad in actividad_reciente:
        # Obtener información del estudiante
        estudiante = db.query(User).filter(User.id == actividad.estudiante_id).first()
        
        # Obtener información del curso
        curso = db.query(Curso).filter(Curso.id == actividad.curso_id).first()
        
        actividad_data = {
            "id": actividad.id,
            "estudiante_nombre": f"{estudiante.first_name} {estudiante.last_name}" if estudiante else "Desconocido",
            "curso_nombre": curso.nombre if curso else "Desconocido",
            "nota_anterior": actividad.nota_anterior,
            "nota_nueva": actividad.nota_nueva,
            "fecha": actividad.created_at
        }
        actividad_response.append(actividad_data)
    
    # Construir estadísticas
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
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
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
            "fecha_matricula": fecha_matricula
        })
    
    return estudiantes_response

@router.get("/courses/{curso_id}/grades", response_model=List[NotaResponse])
def get_course_grades(
    curso_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_docente_user)
):
    """
    Devuelve todas las notas registradas para los estudiantes del curso indicado,
    solo si el curso pertenece al docente autenticado.
    """
    # Verificar que el curso exista y pertenezca al docente
    curso = db.query(Curso).filter(
        Curso.id == curso_id,
        Curso.docente_id == current_user.id
    ).first()

    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado o no pertenece al docente")

    # Obtener las notas de ese curso
    notas = (
        db.query(Nota, User)
        .join(User, User.id == Nota.estudiante_id)
        .filter(Nota.curso_id == curso_id)
        .all()
    )

    if not notas:
        return []

    # Formatear la respuesta
    notas_data = []
    for nota, estudiante in notas:
        notas_data.append(NotaResponse(
            id=nota.id,
            estudiante_id=estudiante.id,
            estudiante_nombre=f"{estudiante.first_name} {estudiante.last_name}",
            tipo_evaluacion=nota.tipo_evaluacion,
            nota=float(nota.nota),
            peso=float(nota.peso),
            fecha_evaluacion=str(nota.fecha_evaluacion),
            observaciones=nota.observaciones
        ))

    return notas_data

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
        # Obtener todas las notas del estudiante en este curso
        notas = db.query(Nota).filter(
            Nota.estudiante_id == estudiante.id,
            Nota.curso_id == curso_id
        ).order_by(Nota.fecha_evaluacion).all()
        
        # Convertir notas a formato de diccionario
        notas_data = []
        for nota in notas:
            notas_data.append({
                "id": nota.id,
                "tipo_evaluacion": nota.tipo_evaluacion,
                "valor_nota": float(nota.valor_nota),
                "peso": float(nota.peso),
                "fecha_evaluacion": nota.fecha_evaluacion.strftime("%Y-%m-%d"),
                "observaciones": nota.observaciones,
                "created_at": nota.created_at
            })
        
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

@router.post("/grades", response_model=NotaDocenteResponse)
def create_grade(
    nota_data: NotaCreate,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Crear una nueva nota para un estudiante en un curso"""
    
    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == nota_data.curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no tienes permisos para acceder"
        )
    
    # Verificar que el estudiante está matriculado en el ciclo del curso
    matricula = db.query(Matricula).filter(
        Matricula.estudiante_id == nota_data.estudiante_id,
        Matricula.ciclo_id == curso.ciclo_id,
        Matricula.is_active == True
    ).first()
    
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El estudiante no está matriculado en este ciclo"
        )
    
    # Obtener el peso según el tipo de evaluación
    from app.shared.grade_calculator import GradeCalculator
    peso = GradeCalculator.obtener_peso_por_tipo(nota_data.tipo_evaluacion)
    
    # Convertir fecha de string a date
    from datetime import datetime
    fecha_evaluacion = datetime.strptime(nota_data.fecha_evaluacion, "%Y-%m-%d").date()
    
    # Crear nueva nota
    new_nota = Nota(
        estudiante_id=nota_data.estudiante_id,
        curso_id=nota_data.curso_id,
        tipo_evaluacion=nota_data.tipo_evaluacion,
        valor_nota=nota_data.valor_nota,
        peso=peso,
        fecha_evaluacion=fecha_evaluacion,
        observaciones=nota_data.observaciones
    )
    
    db.add(new_nota)
    db.commit()
    db.refresh(new_nota)
    
    # Registrar en historial
    historial = HistorialNota(
        nota_id=new_nota.id,
        estudiante_id=nota_data.estudiante_id,
        curso_id=nota_data.curso_id,
        nota_anterior=None,
        nota_nueva=nota_data.valor_nota,
        modificado_por=current_user.id
    )
    
    db.add(historial)
    db.commit()
    
    # Obtener información del estudiante para la respuesta
    estudiante = db.query(User).filter(User.id == nota_data.estudiante_id).first()
    
    return {
        "id": new_nota.id,
        "estudiante_id": new_nota.estudiante_id,
        "estudiante_nombre": f"{estudiante.first_name} {estudiante.last_name}",
        "curso_id": new_nota.curso_id,
        "curso_nombre": curso.nombre,
        "tipo_evaluacion": new_nota.tipo_evaluacion,
        "valor_nota": new_nota.valor_nota,
        "peso": new_nota.peso,
        "fecha_evaluacion": new_nota.fecha_evaluacion.strftime("%Y-%m-%d"),
        "observaciones": new_nota.observaciones,
        "created_at": new_nota.created_at,
        "updated_at": new_nota.updated_at
    }

@router.put("/grades/{nota_id}", response_model=NotaDocenteResponse)
def update_grade(
    nota_id: int,
    nota_data: NotaUpdate,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Actualizar una nota existente"""
    
    # Obtener la nota
    nota = db.query(Nota).filter(Nota.id == nota_id).first()
    
    if not nota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota no encontrada"
        )
    
    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == nota.curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para modificar esta nota"
        )
    
    # Guardar valor anterior para el historial
    valor_anterior = nota.valor_nota
    
    # Actualizar campos
    if nota_data.valor_nota is not None:
        nota.valor_nota = nota_data.valor_nota
    
    if nota_data.fecha_evaluacion is not None:
        from datetime import datetime
        nota.fecha_evaluacion = datetime.strptime(nota_data.fecha_evaluacion, "%Y-%m-%d").date()
    
    if nota_data.observaciones is not None:
        nota.observaciones = nota_data.observaciones
    
    db.commit()
    db.refresh(nota)
    
    # Registrar en historial si el valor cambió
    if valor_anterior != nota.valor_nota:
        historial = HistorialNota(
            nota_id=nota.id,
            estudiante_id=nota.estudiante_id,
            curso_id=nota.curso_id,
            nota_anterior=valor_anterior,
            nota_nueva=nota.valor_nota,
            modificado_por=current_user.id
        )
        
        db.add(historial)
        db.commit()
    
    # Obtener información del estudiante para la respuesta
    estudiante = db.query(User).filter(User.id == nota.estudiante_id).first()
    
    return {
        "id": nota.id,
        "estudiante_id": nota.estudiante_id,
        "estudiante_nombre": f"{estudiante.first_name} {estudiante.last_name}" if estudiante else "Desconocido",
        "curso_id": nota.curso_id,
        "curso_nombre": curso.nombre,
        "tipo_evaluacion": nota.tipo_evaluacion,
        "valor_nota": nota.valor_nota,
        "peso": nota.peso,
        "fecha_evaluacion": nota.fecha_evaluacion.strftime("%Y-%m-%d"),
        "observaciones": nota.observaciones,
        "created_at": nota.created_at,
        "updated_at": nota.updated_at
    }

@router.post("/courses/{curso_id}/grades/bulk", response_model=dict)
def update_grades_bulk(
    curso_id: int,
    notas_data: ActualizacionMasivaNotas,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Actualizar múltiples notas de un curso en una sola operación"""
    
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
    
    # Procesar cada nota
    actualizadas = 0
    creadas = 0
    errores = []
    
    for nota_item in notas_data.notas:
        try:
            # Verificar que el estudiante está matriculado en el curso
            matricula = db.query(Matricula).filter(
                Matricula.estudiante_id == nota_item.estudiante_id,
                Matricula.curso_id == curso_id,
                Matricula.is_active == True
            ).first()
            
            if not matricula:
                errores.append(f"El estudiante {nota_item.estudiante_id} no está matriculado en este curso")
                continue
            
            # Buscar si ya existe una nota para este estudiante
            nota = db.query(Nota).filter(
                Nota.estudiante_id == nota_item.estudiante_id,
                Nota.curso_id == curso_id
            ).first()
            
            nota_anterior = None
            
            if nota:
                # Actualizar nota existente
                nota_anterior = nota.nota_final
                
                if nota_item.nota1 is not None:
                    nota.nota1 = nota_item.nota_1
                if nota_item.nota2 is not None:
                    nota.nota2 = nota_item.nota_2
                if nota_item.nota3 is not None:
                    nota.nota3 = nota_item.nota_3
                if nota_item.nota4 is not None:
                    nota.nota4 = nota_item.nota_4
                
                actualizadas += 1
            else:
                # Crear nueva nota
                nota = Nota(
                    estudiante_id=nota_item.estudiante_id,
                    curso_id=curso_id,
                    nota1=nota_item.nota1,
                    nota2=nota_item.nota2,
                    nota3=nota_item.nota3,
                    nota4=nota_item.nota4
                )
                db.add(nota)
                creadas += 1
            
            # Calcular nota final
            notas = [
                nota.nota1 if nota.nota1 is not None else Decimal('0'),
                nota.nota2 if nota.nota2 is not None else Decimal('0'),
                nota.nota3 if nota.nota3 is not None else Decimal('0'),
                nota.nota4 if nota.nota4 is not None else Decimal('0')
            ]
            
            # Calcular promedio solo de las notas que no son cero
            notas_validas = [n for n in notas if n > Decimal('0')]
            nota_final = sum(notas_validas) / len(notas_validas) if notas_validas else Decimal('0')
            nota_final = round(nota_final, 2)
            
            nota.nota_final = nota_final
            
            # Actualizar estado
            nota.estado = "APROBADO" if nota_final >= Decimal('10.5') else "DESAPROBADO"
            
            db.commit()
            db.refresh(nota)
            
            # Registrar en historial si es una nota nueva o si la nota final cambió
            if nota_anterior is None or nota_anterior != nota.nota_final:
                historial = HistorialNota(
                    nota_id=nota.id,
                    estudiante_id=nota.estudiante_id,
                    curso_id=nota.curso_id,
                    nota_anterior=nota_anterior,
                    nota_nueva=nota.nota_final,
                    modificado_por=current_user.id
                )
                
                db.add(historial)
                db.commit()
            
        except Exception as e:
            errores.append(f"Error al procesar estudiante {nota_item.estudiante_id}: {str(e)}")
    
    return {
        "mensaje": "Proceso completado",
        "notas_actualizadas": actualizadas,
        "notas_creadas": creadas,
        "errores": errores
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
    
    db.commit()
    db.refresh(curso)
    
    # Obtener información adicional para la respuesta
    ciclo = db.query(Ciclo).filter(Ciclo.id == curso.ciclo_id).first()
    
    estudiantes_count = db.query(Matricula).filter(
        Matricula.curso_id == curso.id,
        Matricula.is_active == True
    ).count()
    
    return {
        "id": curso.id,
        "nombre": curso.nombre,
        "ciclo_id": curso.ciclo_id,
        "docente_id": curso.docente_id,
        "is_active": curso.is_active,
        "created_at": curso.created_at,
        "ciclo_nombre": ciclo.nombre if ciclo else None,
        "total_estudiantes": estudiantes_count
    }

# Nuevos endpoints para el sistema de calificaciones mejorado

@router.get("/courses/{curso_id}/students/{estudiante_id}/final-grade", response_model=PromedioFinalResponse)
def get_student_final_grade(
    curso_id: int,
    estudiante_id: int,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener el promedio final de un estudiante en un curso específico"""
    
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
    
    # Verificar que el estudiante está matriculado en el curso
    matricula = db.query(Matricula).filter(
        Matricula.estudiante_id == estudiante_id,
        Matricula.curso_id == curso_id,
        Matricula.is_active == True
    ).first()
    
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El estudiante no está matriculado en este curso"
        )
    
    # Calcular promedio final usando GradeCalculator
    from app.shared.grade_calculator import GradeCalculator
    resultado = GradeCalculator.calcular_promedio_final(estudiante_id, curso_id, db)
    
    return {
        "estudiante_id": estudiante_id,
        "curso_id": curso_id,
        "promedio_final": resultado["promedio_final"],
        "estado": resultado["estado"],
        "detalle": resultado["detalle"]
    }

@router.get("/courses/{curso_id}/students/{estudiante_id}/grade-structure", response_model=EstructuraNotasResponse)
def get_student_grade_structure(
    curso_id: int,
    estudiante_id: int,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener la estructura de notas de un estudiante (validar si tiene todas las notas requeridas)"""
    
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
    
    # Verificar que el estudiante está matriculado en el curso
    matricula = db.query(Matricula).filter(
        Matricula.estudiante_id == estudiante_id,
        Matricula.curso_id == curso_id,
        Matricula.is_active == True
    ).first()
    
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El estudiante no está matriculado en este curso"
        )
    
    # Validar estructura usando GradeCalculator
    from app.shared.grade_calculator import GradeCalculator
    estructura = GradeCalculator.validar_estructura_ciclo(estudiante_id, curso_id, db)
    
    return {
        "estudiante_id": estudiante_id,
        "curso_id": curso_id,
        "notas_semanales": estructura["notas_semanales"],
        "notas_practicas": estructura["notas_practicas"],
        "notas_parciales": estructura["notas_parciales"],
        "estructura_completa": estructura["estructura_completa"]
    }

@router.get("/courses/{curso_id}/all-final-grades", response_model=List[PromedioFinalResponse])
def get_all_students_final_grades(
    curso_id: int,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener los promedios finales de todos los estudiantes de un curso"""
    
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
    
    # Obtener todos los estudiantes matriculados en el curso
    matriculas = db.query(Matricula).filter(
        Matricula.curso_id == curso_id,
        Matricula.is_active == True
    ).all()
    
    resultados = []
    from app.shared.grade_calculator import GradeCalculator
    
    for matricula in matriculas:
        resultado = GradeCalculator.calcular_promedio_final(matricula.estudiante_id, curso_id, db)
        resultados.append({
            "estudiante_id": matricula.estudiante_id,
            "curso_id": curso_id,
            "promedio_final": resultado["promedio_final"],
            "estado": resultado["estado"],
            "detalle": resultado["detalle"]
        })
    
    return resultados