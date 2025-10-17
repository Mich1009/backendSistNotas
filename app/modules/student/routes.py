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
    MatriculaResponse,
    EstudianteDashboard, EstadisticasEstudiante,
    PromedioFinalEstudianteResponse, NotasPorTipoResponse,CursoConNotasResponse,NotaEstudianteResponse  
)

router = APIRouter(prefix="/student", tags=["Estudiante"])

@router.get("/dashboard", response_model=EstudianteDashboard)
def get_student_dashboard(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener dashboard completo del estudiante - CON CAMPOS CORRECTOS"""
    
    try:
        # Información básica del estudiante
        estudiante_info = {
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email,
            "dni": current_user.dni
        }

        # Obtener ciclo activo
        ciclo_actual = db.query(Ciclo).filter(
            Ciclo.is_active == True
        ).first()

        if not ciclo_actual:
            return {
                "estudiante_info": estudiante_info,
                "cursos_actuales": [],
                "notas_recientes": [],
                "estadisticas": {
                    "total_cursos": 0,
                    "promedio_general": 0,
                    "cursos_aprobados": 0,
                    "cursos_desaprobados": 0,
                    "creditos_completados": 0
                }
            }

        # Cursos actuales - VERSIÓN CORRECTA
        cursos_actuales = db.query(Curso).filter(
            Curso.ciclo_id == ciclo_actual.id
        ).all()

        cursos_formateados = []
        for curso in cursos_actuales:
            cursos_formateados.append({
                "id": curso.id,
                "nombre": curso.nombre,
                "codigo": f"CUR-{curso.id}",
                "docente_nombre": f"{curso.docente.first_name} {curso.docente.last_name}" if curso.docente else "Sin asignar",
                "ciclo_nombre": ciclo_actual.nombre,
                "creditos": 3
            })

        # Notas recientes - VERSIÓN CORREGIDA (SIN JOIN PROBLEMÁTICO)
        curso_ids = [curso.id for curso in cursos_actuales]
        notas_recientes = db.query(Nota).filter(
            Nota.estudiante_id == current_user.id,
            Nota.curso_id.in_(curso_ids)
        ).order_by(Nota.updated_at.desc()).limit(5).all()
        
        notas_formateadas = []
        for nota in notas_recientes:
            notas_formateadas.append({
                "id": nota.id,
                "curso_nombre": nota.curso.nombre,
                "curso_codigo": f"CUR-{nota.curso.id}",
                "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}" if nota.curso.docente else "Sin asignar",
                "ciclo_nombre": ciclo_actual.nombre,
                
                # SOLO CAMPOS QUE EXISTEN EN EL MODELO
                "evaluacion1": float(nota.evaluacion1) if nota.evaluacion1 else None,
                "evaluacion2": float(nota.evaluacion2) if nota.evaluacion2 else None,
                "evaluacion3": float(nota.evaluacion3) if nota.evaluacion3 else None,
                "evaluacion4": float(nota.evaluacion4) if nota.evaluacion4 else None,
                "evaluacion5": float(nota.evaluacion5) if nota.evaluacion5 else None,
                "evaluacion6": float(nota.evaluacion6) if nota.evaluacion6 else None,
                "evaluacion7": float(nota.evaluacion7) if nota.evaluacion7 else None,
                "evaluacion8": float(nota.evaluacion8) if nota.evaluacion8 else None,
                
                "practica1": float(nota.practica1) if nota.practica1 else None,
                "practica2": float(nota.practica2) if nota.practica2 else None,
                "practica3": float(nota.practica3) if nota.practica3 else None,
                "practica4": float(nota.practica4) if nota.practica4 else None,
                
                "parcial1": float(nota.parcial1) if nota.parcial1 else None,
                "parcial2": float(nota.parcial2) if nota.parcial2 else None,
                
                "promedio_final": float(nota.promedio_final) if nota.promedio_final else None,
                "estado": nota.estado,
                "fecha_actualizacion": nota.updated_at.isoformat() if nota.updated_at else nota.created_at.isoformat()
            })

        # CALCULAR ESTADÍSTICAS - ESTO FALTABA
        total_cursos = len(cursos_actuales)
        
        # Calcular promedios y cursos aprobados
        promedios_por_curso = []
        cursos_aprobados = 0
        
        for curso in cursos_actuales:
            # Obtener notas del curso
            notas_curso = db.query(Nota).filter(
                Nota.estudiante_id == current_user.id,
                Nota.curso_id == curso.id
            ).all()
            
            if notas_curso:
                # Calcular promedio del curso
                todas_notas_curso = []
                for nota in notas_curso:
                    campos = [
                        'evaluacion1', 'evaluacion2', 'evaluacion3', 'evaluacion4',
                        'evaluacion5', 'evaluacion6', 'evaluacion7', 'evaluacion8',
                        'practica1', 'practica2', 'practica3', 'practica4',
                        'parcial1', 'parcial2'
                    ]
                    
                    for campo in campos:
                        valor = getattr(nota, campo)
                        if valor is not None:
                            todas_notas_curso.append(float(valor))
                
                if todas_notas_curso:
                    promedio_curso = sum(todas_notas_curso) / len(todas_notas_curso)
                    promedios_por_curso.append(promedio_curso)
                    
                    if promedio_curso >= 10.5:
                        cursos_aprobados += 1

        # Calcular promedio general
        promedio_general = round(sum(promedios_por_curso) / len(promedios_por_curso), 2) if promedios_por_curso else 0
        
        # Calcular créditos
        creditos_completados = cursos_aprobados * 3

        # DEFINIR LAS ESTADÍSTICAS - ESTO FALTABA
        estadisticas = {
            "total_cursos": total_cursos,
            "promedio_general": promedio_general,
            "cursos_aprobados": cursos_aprobados,
            "cursos_desaprobados": total_cursos - cursos_aprobados,
            "creditos_completados": creditos_completados
        }

        return {
            "estudiante_info": estudiante_info,
            "cursos_actuales": cursos_formateados,
            "notas_recientes": notas_formateadas,
            "estadisticas": estadisticas
        }

    except Exception as e:
        print(f"Error in get_student_dashboard: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        return {
            "estudiante_info": {
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "email": current_user.email,
                "dni": current_user.dni
            },
            "cursos_actuales": [],
            "notas_recientes": [],
            "estadisticas": {
                "total_cursos": 0,
                "promedio_general": 0,
                "cursos_aprobados": 0,
                "cursos_desaprobados": 0,
                "creditos_completados": 0
            }
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
    curso_id: Optional[int] = Query(None, description="Filtrar por curso específico"),
    ciclo_id: Optional[int] = Query(None, description="Filtrar por ciclo específico"),
    docente_id: Optional[int] = Query(None, description="Filtrar por docente específico")
):
    """Obtener notas del estudiante con filtros por curso, ciclo y docente"""
    
    try:
        # Construir query base
        query = db.query(Nota).filter(
            Nota.estudiante_id == current_user.id
        ).options(
            joinedload(Nota.curso).joinedload(Curso.docente),
            joinedload(Nota.curso).joinedload(Curso.ciclo)
        )
        
        # Aplicar filtros
        if curso_id:
            query = query.filter(Nota.curso_id == curso_id)
        
        if ciclo_id:
            query = query.join(Curso).filter(Curso.ciclo_id == ciclo_id)
        
        if docente_id:
            query = query.join(Curso).filter(Curso.docente_id == docente_id)
        
        notas = query.order_by(Nota.created_at.desc()).all()
        
        # Convertir a formato de respuesta
        notas_response = []
        for nota in notas:
            # Calcular promedio automáticamente si no existe
            promedio_final = nota.promedio_final
            if promedio_final is None:
                # Calcular promedio basado en las notas existentes
                all_grades = []
                
                # Evaluaciones
                for i in range(1, 9):
                    eval_grade = getattr(nota, f'evaluacion{i}')
                    if eval_grade is not None:
                        all_grades.append(float(eval_grade))
                
                # Prácticas
                for i in range(1, 5):
                    prac_grade = getattr(nota, f'practica{i}')
                    if prac_grade is not None:
                        all_grades.append(float(prac_grade))
                
                # Parciales
                for i in range(1, 3):
                    par_grade = getattr(nota, f'parcial{i}')
                    if par_grade is not None:
                        all_grades.append(float(par_grade))
                
                if all_grades:
                    promedio_final = sum(all_grades) / len(all_grades)
            
            # Determinar estado
            estado = nota.estado
            if estado is None and promedio_final is not None:
                estado = "APROBADO" if promedio_final >= 10.5 else "DESAPROBADO"
            
            nota_data = NotaEstudianteResponse(
                id=nota.id,
                curso_id=nota.curso_id,
                curso_nombre=nota.curso.nombre,
                docente_nombre=f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}" if nota.curso.docente else "Sin asignar",
                ciclo_nombre=nota.curso.ciclo.nombre if nota.curso.ciclo else "Sin ciclo",
                tipo_evaluacion=nota.tipo_evaluacion,
                
                # Campos del sistema nuevo
                evaluacion1=nota.evaluacion1,
                evaluacion2=nota.evaluacion2,
                evaluacion3=nota.evaluacion3,
                evaluacion4=nota.evaluacion4,
                evaluacion5=nota.evaluacion5,
                evaluacion6=nota.evaluacion6,
                evaluacion7=nota.evaluacion7,
                evaluacion8=nota.evaluacion8,
                
                practica1=nota.practica1,
                practica2=nota.practica2,
                practica3=nota.practica3,
                practica4=nota.practica4,
                
                parcial1=nota.parcial1,
                parcial2=nota.parcial2,
                
                promedio_final=promedio_final,
                estado=estado,
                
                peso=nota.peso,
                fecha_evaluacion=nota.fecha_evaluacion.strftime("%Y-%m-%d"),
                observaciones=nota.observaciones,
                created_at=nota.created_at
            )
            notas_response.append(nota_data)
        
        return notas_response
        
    except Exception as e:
        print(f"Error in get_student_grades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las notas del estudiante"
        )

@router.get("/grades/filters")
def get_student_grades_filters(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener opciones de filtro para las calificaciones del estudiante"""
    
    try:
        # Obtener cursos únicos del estudiante
        cursos = db.query(Curso).join(Nota).filter(
            Nota.estudiante_id == current_user.id
        ).options(
            joinedload(Curso.docente),
            joinedload(Curso.ciclo)
        ).distinct().all()
        
        # Obtener ciclos únicos
        ciclos = db.query(Ciclo).join(Curso).join(Nota).filter(
            Nota.estudiante_id == current_user.id
        ).distinct().all()
        
        # Obtener docentes únicos
        docentes = db.query(User).join(Curso).join(Nota).filter(
            Nota.estudiante_id == current_user.id,
            User.role == "docente"
        ).distinct().all()
        
        cursos_filters = [
            {
                "id": curso.id,
                "nombre": curso.nombre,
                "ciclo_nombre": curso.ciclo.nombre if curso.ciclo else "Sin ciclo"
            }
            for curso in cursos
        ]
        
        ciclos_filters = [
            {
                "id": ciclo.id,
                "nombre": ciclo.nombre,
                "año": ciclo.año
            }
            for ciclo in ciclos
        ]
        
        docentes_filters = [
            {
                "id": docente.id,
                "nombre": f"{docente.first_name} {docente.last_name}"
            }
            for docente in docentes
        ]
        
        return {
            "cursos": cursos_filters,
            "ciclos": ciclos_filters,
            "docentes": docentes_filters
        }
        
    except Exception as e:
        print(f"Error in get_student_grades_filters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener los filtros de calificaciones"
        )

@router.get("/grades/statistics", response_model=EstadisticasEstudiante)
def get_student_grades_statistics(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db),
    curso_id: Optional[int] = Query(None, description="Filtrar por curso específico"),
    ciclo_id: Optional[int] = Query(None, description="Filtrar por ciclo específico")
):
    """Obtener estadísticas de las calificaciones del estudiante"""
    
    try:
        # Obtener notas con filtros
        query = db.query(Nota).filter(
            Nota.estudiante_id == current_user.id
        ).options(
            joinedload(Nota.curso)
        )
        
        if curso_id:
            query = query.filter(Nota.curso_id == curso_id)
        
        if ciclo_id:
            query = query.join(Curso).filter(Curso.ciclo_id == ciclo_id)
        
        notas = query.all()
        
        # Calcular estadísticas
        total_notas = len(notas)
        
        # Calcular promedios por curso
        cursos_promedios = {}
        for nota in notas:
            if nota.curso_id not in cursos_promedios:
                cursos_promedios[nota.curso_id] = {
                    "nombre": nota.curso.nombre,
                    "promedios": []
                }
            
            # Calcular promedio de esta nota
            all_grades = []
            
            # Evaluaciones
            for i in range(1, 9):
                eval_grade = getattr(nota, f'evaluacion{i}')
                if eval_grade is not None:
                    all_grades.append(float(eval_grade))
            
            # Prácticas
            for i in range(1, 5):
                prac_grade = getattr(nota, f'practica{i}')
                if prac_grade is not None:
                    all_grades.append(float(prac_grade))
            
            # Parciales
            for i in range(1, 3):
                par_grade = getattr(nota, f'parcial{i}')
                if par_grade is not None:
                    all_grades.append(float(par_grade))
            
            if all_grades:
                nota_promedio = sum(all_grades) / len(all_grades)
                cursos_promedios[nota.curso_id]["promedios"].append(nota_promedio)
        
        # Calcular estadísticas generales
        promedios_por_curso = []
        cursos_aprobados = 0
        cursos_desaprobados = 0
        
        for curso_data in cursos_promedios.values():
            if curso_data["promedios"]:
                curso_promedio = sum(curso_data["promedios"]) / len(curso_data["promedios"])
                promedios_por_curso.append(curso_promedio)
                if curso_promedio >= 10.5:
                    cursos_aprobados += 1
                else:
                    cursos_desaprobados += 1
        
        promedio_general = None
        if promedios_por_curso:
            promedio_general = sum(promedios_por_curso) / len(promedios_por_curso)
        
        total_cursos = len(cursos_promedios)
        
        return EstadisticasEstudiante(
            total_cursos=total_cursos,
            promedio_general=promedio_general,
            cursos_aprobados=cursos_aprobados,
            cursos_desaprobados=cursos_desaprobados,
            creditos_completados=cursos_aprobados  # Asumiendo 1 crédito por curso aprobado
        )
        
    except Exception as e:
        print(f"Error in get_student_grades_statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las estadísticas de calificaciones"
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
    
    # Convertir a formato de respuesta - USANDO CAMPOS CORRECTOS
    notas_response = []
    for nota in notas:
        # Calcular promedio si no existe
        promedio_final = nota.promedio_final
        if promedio_final is None:
            all_grades = []
            for i in range(1, 9):
                eval_grade = getattr(nota, f'evaluacion{i}')
                if eval_grade is not None:
                    all_grades.append(float(eval_grade))
            
            for i in range(1, 5):
                prac_grade = getattr(nota, f'practica{i}')
                if prac_grade is not None:
                    all_grades.append(float(prac_grade))
            
            for i in range(1, 3):
                par_grade = getattr(nota, f'parcial{i}')
                if par_grade is not None:
                    all_grades.append(float(par_grade))
            
            if all_grades:
                promedio_final = sum(all_grades) / len(all_grades)
        
        estado = nota.estado
        if estado is None and promedio_final is not None:
            estado = "APROBADO" if promedio_final >= 10.5 else "DESAPROBADO"
        
        nota_data = NotaEstudianteResponse(
            id=nota.id,
            curso_id=nota.curso_id,
            curso_nombre=nota.curso.nombre,
            docente_nombre=f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}" if nota.curso.docente else "Sin asignar",
            ciclo_nombre=nota.curso.ciclo.nombre if nota.curso.ciclo else "Sin ciclo",
            tipo_evaluacion=nota.tipo_evaluacion,
            
            # Campos del sistema nuevo
            evaluacion1=nota.evaluacion1,
            evaluacion2=nota.evaluacion2,
            evaluacion3=nota.evaluacion3,
            evaluacion4=nota.evaluacion4,
            evaluacion5=nota.evaluacion5,
            evaluacion6=nota.evaluacion6,
            evaluacion7=nota.evaluacion7,
            evaluacion8=nota.evaluacion8,
            
            practica1=nota.practica1,
            practica2=nota.practica2,
            practica3=nota.practica3,
            practica4=nota.practica4,
            
            parcial1=nota.parcial1,
            parcial2=nota.parcial2,
            
            promedio_final=promedio_final,
            estado=estado,
            
            peso=nota.peso,
            fecha_evaluacion=nota.fecha_evaluacion.strftime("%Y-%m-%d"),
            observaciones=nota.observaciones,
            created_at=nota.created_at
        )
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
        Matricula.ciclo_id == curso_id,  # CORREGIR: esto debería ser curso_id?
        Matricula.estado == "activa"
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
    
    # Agrupar notas por tipo - USANDO CAMPOS CORRECTOS
    evaluaciones_semanales = []
    evaluaciones_practicas = []
    evaluaciones_parciales = []
    
    for nota in notas:
        # Calcular promedio si no existe
        promedio_final = nota.promedio_final
        if promedio_final is None:
            all_grades = []
            for i in range(1, 9):
                eval_grade = getattr(nota, f'evaluacion{i}')
                if eval_grade is not None:
                    all_grades.append(float(eval_grade))
            
            for i in range(1, 5):
                prac_grade = getattr(nota, f'practica{i}')
                if prac_grade is not None:
                    all_grades.append(float(prac_grade))
            
            for i in range(1, 3):
                par_grade = getattr(nota, f'parcial{i}')
                if par_grade is not None:
                    all_grades.append(float(par_grade))
            
            if all_grades:
                promedio_final = sum(all_grades) / len(all_grades)
        
        estado = nota.estado
        if estado is None and promedio_final is not None:
            estado = "APROBADO" if promedio_final >= 10.5 else "DESAPROBADO"
        
        nota_data = NotaEstudianteResponse(
            id=nota.id,
            curso_id=nota.curso_id,
            curso_nombre=nota.curso.nombre,
            docente_nombre=f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}" if nota.curso.docente else "Sin asignar",
            tipo_evaluacion=nota.tipo_evaluacion,
            
            # Campos del sistema nuevo
            evaluacion1=nota.evaluacion1,
            evaluacion2=nota.evaluacion2,
            evaluacion3=nota.evaluacion3,
            evaluacion4=nota.evaluacion4,
            evaluacion5=nota.evaluacion5,
            evaluacion6=nota.evaluacion6,
            evaluacion7=nota.evaluacion7,
            evaluacion8=nota.evaluacion8,
            
            practica1=nota.practica1,
            practica2=nota.practica2,
            practica3=nota.practica3,
            practica4=nota.practica4,
            
            parcial1=nota.parcial1,
            parcial2=nota.parcial2,
            
            promedio_final=promedio_final,
            estado=estado,
            
            peso=nota.peso,
            fecha_evaluacion=nota.fecha_evaluacion.strftime("%Y-%m-%d"),
            observaciones=nota.observaciones,
            created_at=nota.created_at
        )
        
        if nota.tipo_evaluacion == "SEMANAL":
            evaluaciones_semanales.append(nota_data)
        elif nota.tipo_evaluacion == "PRACTICA":
            evaluaciones_practicas.append(nota_data)
        elif nota.tipo_evaluacion == "PARCIAL":
            evaluaciones_parciales.append(nota_data)
    
    # Calcular promedio final
    from app.shared.grade_calculator import GradeCalculator
    resultado = GradeCalculator.calcular_promedio_final(current_user.id, curso_id, db)
    
    return NotasPorTipoResponse(
        curso_id=curso_id,
        curso_nombre=curso.nombre,
        evaluaciones_semanales=evaluaciones_semanales,
        evaluaciones_practicas=evaluaciones_practicas,
        evaluaciones_parciales=evaluaciones_parciales,
        promedio_final=resultado["promedio_final"],
        estado=resultado["estado"]
    )

@router.get("/courses-with-grades", response_model=List[CursoConNotasResponse])
def get_student_courses_with_grades(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener cursos del estudiante con todas sus notas - SISTEMA NUEVO"""
    
    try:
        # Obtener cursos del estudiante
        cursos_response = get_student_courses(current_user, db)
        
        cursos_con_notas = []
        
        for curso_data in cursos_response:
            # Obtener notas para este curso
            notas = db.query(Nota).filter(
                Nota.estudiante_id == current_user.id,
                Nota.curso_id == curso_data.id
            ).options(
                joinedload(Nota.curso).joinedload(Curso.docente)
            ).all()
            
            # Convertir notas a formato nuevo
            notas_response = []
            for nota in notas:
                nota_data = NotaEstudianteResponse(
                    id=nota.id,
                    curso_id=nota.curso_id,
                    curso_nombre=nota.curso.nombre,
                    docente_nombre=f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}" if nota.curso.docente else "Sin asignar",
                    tipo_evaluacion=nota.tipo_evaluacion,
                    
                    # Campos del sistema nuevo
                    evaluacion1=nota.evaluacion1,
                    evaluacion2=nota.evaluacion2,
                    evaluacion3=nota.evaluacion3,
                    evaluacion4=nota.evaluacion4,
                    evaluacion5=nota.evaluacion5,
                    evaluacion6=nota.evaluacion6,
                    evaluacion7=nota.evaluacion7,
                    evaluacion8=nota.evaluacion8,
                    
                    practica1=nota.practica1,
                    practica2=nota.practica2,
                    practica3=nota.practica3,
                    practica4=nota.practica4,
                    
                    parcial1=nota.parcial1,
                    parcial2=nota.parcial2,
                    
                    promedio_final=nota.promedio_final,
                    estado=nota.estado,
                    
                    peso=nota.peso,
                    fecha_evaluacion=nota.fecha_evaluacion.strftime("%Y-%m-%d"),
                    observaciones=nota.observaciones,
                    created_at=nota.created_at
                )
                notas_response.append(nota_data)
            
            # Calcular promedio final del curso
            from app.shared.grade_calculator import GradeCalculator
            resultado = GradeCalculator.calcular_promedio_final(current_user.id, curso_data.id, db)
            
            curso_con_notas = CursoConNotasResponse(
                curso=curso_data,
                notas=notas_response,
                promedio_final=resultado["promedio_final"],
                estado=resultado["estado"]
            )
            
            cursos_con_notas.append(curso_con_notas)
        
        return cursos_con_notas
        
    except Exception as e:
        print(f"Error in get_student_courses_with_grades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener los cursos con notas del estudiante"
        )