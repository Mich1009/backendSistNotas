from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from ...database import get_db
from ..auth.dependencies import get_estudiante_user
from ..auth.models import User
from .models import Ciclo, Curso, Nota
from .schemas import EstudianteDashboard, RendimientoAcademicoCiclo, RendimientoCicloDetallado
from ...shared.models import Matricula
from ...shared.grade_calculator import GradeCalculator

# Importar los routers de los módulos separados
from .grades_routes import router as grades_router
from .courses_routes import router as courses_router
from .schedule_routes import router as schedule_router
from .profile_routes import router as profile_router

router = APIRouter(prefix="/student", tags=["Estudiante - Dashboard"])

# Endpoint de rendimiento académico con autenticación y cursos detallados
@router.get("/academic-performance", response_model=List[RendimientoCicloDetallado])
def get_academic_performance(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener el rendimiento académico con cursos detallados del estudiante autenticado"""
    
    try:
        # Usar el ID del usuario autenticado
        estudiante_id = current_user.id
        
        # Obtener todas las matrículas del estudiante con información del ciclo
        matriculas = db.query(Matricula).options(
            joinedload(Matricula.ciclo)
        ).filter(
            Matricula.estudiante_id == estudiante_id,
            Matricula.is_active == True
        ).all()
        
        if not matriculas:
            return []
        
        performance_data = []
        calculator = GradeCalculator()
        
        for matricula in matriculas:
            # Obtener todos los cursos del ciclo
            cursos_ciclo = db.query(Curso).filter(
                Curso.ciclo_id == matricula.ciclo_id,
                Curso.is_active == True
            ).all()
            
            # Obtener las notas del estudiante para los cursos de este ciclo
            notas_ciclo = db.query(Nota).options(
                joinedload(Nota.curso)
            ).filter(
                Nota.estudiante_id == estudiante_id,
                Nota.curso_id.in_([curso.id for curso in cursos_ciclo]) if cursos_ciclo else []
            ).all()
            
            # Crear diccionario de notas por curso
            notas_por_curso = {nota.curso_id: nota for nota in notas_ciclo}
            
            # Procesar cada curso del ciclo
            cursos_rendimiento = []
            
            for curso in cursos_ciclo:
                nota = notas_por_curso.get(curso.id)
                
                if nota:
                    # Calcular promedio final
                    try:
                        promedio_final = calculator.calcular_promedio_nota(nota)
                    except Exception as e:
                        promedio_final = None
                    
                    # Preparar evaluaciones
                    evaluaciones = {}
                    for i in range(1, 9):
                        eval_val = getattr(nota, f'evaluacion{i}')
                        evaluaciones[f'evaluacion{i}'] = float(eval_val) if eval_val is not None else None
                    
                    # Preparar prácticas
                    practicas = {}
                    for i in range(1, 5):
                        prac_val = getattr(nota, f'practica{i}')
                        practicas[f'practica{i}'] = float(prac_val) if prac_val is not None else None
                    
                    # Preparar parciales
                    parciales = {}
                    for i in range(1, 3):
                        parc_val = getattr(nota, f'parcial{i}')
                        parciales[f'parcial{i}'] = float(parc_val) if parc_val is not None else None
                    
                    # Determinar estado basado en las notas completadas
                    if promedio_final and float(promedio_final) >= 13.0:
                        estado = "Aprobado"
                    elif promedio_final and float(promedio_final) < 13.0:
                        estado = "Desaprobado"
                    else:
                        # Verificar si tiene algunas notas (en curso) o ninguna (pendiente)
                        tiene_notas = any([
                            any(evaluaciones.values()),
                            any(practicas.values()),
                            any(parciales.values())
                        ])
                        estado = "En curso" if tiene_notas else "Pendiente"
                
                else:
                    # Curso sin notas
                    promedio_final = None
                    evaluaciones = {f'evaluacion{i}': None for i in range(1, 9)}
                    practicas = {f'practica{i}': None for i in range(1, 5)}
                    parciales = {f'parcial{i}': None for i in range(1, 3)}
                    estado = "Pendiente"
                
                curso_rendimiento = {
                    "curso_id": curso.id,
                    "curso_nombre": curso.nombre,
                    "promedio_final": float(promedio_final) if promedio_final else None,
                    "estado": estado,
                    "evaluaciones": evaluaciones,
                    "practicas": practicas,
                    "parciales": parciales
                }
                
                cursos_rendimiento.append(curso_rendimiento)
            
            # Calcular estadísticas del ciclo
            numero_cursos = len(cursos_rendimiento)
            
            # Calcular promedio del ciclo (solo cursos con promedio final)
            promedios_validos = [curso["promedio_final"] for curso in cursos_rendimiento if curso["promedio_final"] is not None]
            promedio_ciclo = sum(promedios_validos) / len(promedios_validos) if promedios_validos else None
            
            # Crear el objeto de datos de rendimiento del ciclo
            ciclo_data = {
                "ciclo_id": matricula.ciclo.id,
                "ciclo_nombre": matricula.ciclo.nombre,
                "ciclo_numero": matricula.ciclo.numero,
                "numero_cursos": numero_cursos,
                "promedio_ciclo": round(promedio_ciclo, 2) if promedio_ciclo else None,
                "ciclo_info": {
                    "id": matricula.ciclo.id,
                    "nombre": matricula.ciclo.nombre,
                    "numero": matricula.ciclo.numero
                },
                "cursos": cursos_rendimiento
            }
            
            performance_data.append(ciclo_data)
        
        # Ordenar por número de ciclo
        performance_data.sort(key=lambda x: x["ciclo_info"]["numero"])
        
        return performance_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el rendimiento académico: {str(e)}"
        )

# Incluir los routers de los módulos separados
router.include_router(grades_router)
router.include_router(courses_router)
router.include_router(schedule_router)
router.include_router(profile_router)

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

        # Obtener la última matrícula del estudiante para determinar el ciclo actual
        latest_matricula = db.query(Matricula).join(Ciclo).filter(
            Matricula.estudiante_id == current_user.id
        ).order_by(Ciclo.numero.desc()).first()

        ciclo_actual = latest_matricula.ciclo if latest_matricula else None

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

        # Cursos actuales basados en el ciclo de la última matrícula
        cursos_actuales = db.query(Curso).options(joinedload(Curso.docente)).filter(
            Curso.ciclo_id == ciclo_actual.id
        ).all()

        cursos_formateados = []
        calculator = GradeCalculator()
        for curso in cursos_actuales:
            # Obtener la nota del estudiante para el curso actual
            nota = db.query(Nota).filter(
                Nota.estudiante_id == current_user.id,
                Nota.curso_id == curso.id
            ).first()

            promedio_curso = None
            if nota:
                try:
                    # Usar el calculador para obtener el promedio
                    promedio_curso = calculator.calcular_promedio_final(nota)
                except Exception:
                    promedio_curso = None
            
            # Se mantienen los campos del schema original para evitar errores de validación,
            # y se agrega el promedio. El frontend deberá ser ajustado para mostrarlo.
            cursos_formateados.append({
                "id": curso.id,
                "nombre": curso.nombre,
                "docente_nombre": f"{curso.docente.first_name} {curso.docente.last_name}" if curso.docente else "Sin asignar",
                "ciclo_nombre": ciclo_actual.nombre,
                "creditos": 3,  # Asumiendo un valor por defecto
                "promedio_final": float(promedio_curso) if promedio_curso is not None else None
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
                
                # Calcular promedio final usando el método del modelo
                "promedio_final": float(nota.calcular_promedio_final()) if nota.calcular_promedio_final() else None,
                "estado": nota.obtener_estado(),
                "fecha_actualizacion": nota.updated_at.isoformat() if nota.updated_at else nota.created_at.isoformat()
            })

        # CALCULAR ESTADÍSTICAS DE TODOS LOS CICLOS (APROBADOS Y DESAPROBADOS A LO LARGO DE TODA LA CARRERA)
        # Obtener todas las matrículas activas del estudiante
        matriculas_activas = db.query(Matricula).filter(
            Matricula.estudiante_id == current_user.id,
            Matricula.is_active == True
        ).all()
        
        # Obtener cursos de todos los ciclos en los que está matriculado
        ciclo_ids = [matricula.ciclo_id for matricula in matriculas_activas]
        
        cursos_todos_ciclos = []
        if ciclo_ids:
            cursos_todos_ciclos = db.query(Curso).filter(
                Curso.ciclo_id.in_(ciclo_ids)
            ).all()
        
        # Calcular estadísticas de todos los ciclos usando GradeCalculator
        cursos_aprobados_todos_ciclos = 0
        cursos_desaprobados_todos_ciclos = 0
        cursos_pendientes_todos_ciclos = 0
        promedios_todos_ciclos = []
        
        for curso in cursos_todos_ciclos:
            # Obtener notas del curso
            notas_curso = db.query(Nota).filter(
                Nota.estudiante_id == current_user.id,
                Nota.curso_id == curso.id
            ).all()
            
            if notas_curso:
                # Usar GradeCalculator para calcular el promedio con los pesos correctos
                promedio_calculado = None
                for nota in notas_curso:
                    try:
                        promedio_calculado = GradeCalculator.calcular_promedio_nota(nota)
                        if promedio_calculado is not None:
                            break
                    except Exception:
                        continue
                
                if promedio_calculado is not None:
                    promedio_float = float(promedio_calculado)
                    promedios_todos_ciclos.append(promedio_float)
                    
                    if promedio_float >= 13.0:
                        cursos_aprobados_todos_ciclos += 1
                    else:
                        cursos_desaprobados_todos_ciclos += 1
                else:
                    cursos_pendientes_todos_ciclos += 1
            else:
                cursos_pendientes_todos_ciclos += 1
        
        # Calcular promedio general de todos los ciclos
        promedio_general_todos_ciclos = round(sum(promedios_todos_ciclos) / len(promedios_todos_ciclos), 2) if promedios_todos_ciclos else 0
        
        # Calcular créditos completados de todos los ciclos
        creditos_completados_todos_ciclos = cursos_aprobados_todos_ciclos * 3

        # DEFINIR LAS ESTADÍSTICAS (SOLO DE TODA LA CARRERA)
        estadisticas = {
            "total_cursos_carrera": len(cursos_todos_ciclos),
            "promedio_general_carrera": promedio_general_todos_ciclos,
            "cursos_aprobados_carrera": cursos_aprobados_todos_ciclos,
            "cursos_desaprobados_carrera": cursos_desaprobados_todos_ciclos,
            "cursos_pendientes_carrera": cursos_pendientes_todos_ciclos,
            "creditos_completados_carrera": creditos_completados_todos_ciclos
        }

        return {
            "estudiante_info": estudiante_info,
            "cursos_actuales": cursos_formateados,
            "notas_recientes": notas_formateadas,
            "estadisticas": estadisticas
        }

    except Exception as e:
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