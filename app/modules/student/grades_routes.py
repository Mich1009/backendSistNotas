from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from ...database import get_db
from ..auth.dependencies import get_estudiante_user
from ..auth.models import User
from ...shared.models import Carrera, Ciclo, Curso, Matricula, Nota, DescripcionEvaluacion
from ...shared.grade_calculator import GradeCalculator
from .schemas import (
    EstadisticasEstudiante,
    PromedioFinalEstudianteResponse, 
    NotasPorTipoResponse,
    CursoConNotasResponse,
    NotaEstudianteResponse,
    RendimientoAcademicoCiclo,
    CursoRendimiento,
    RendimientoCicloDetallado
)

router = APIRouter(tags=["Estudiante - Calificaciones"])

@router.get("/grades", response_model=List[NotaEstudianteResponse])
def get_student_grades(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db),
    ciclo_id: Optional[int] = Query(None, description="Filtrar por ciclo específico"),
    docente_id: Optional[int] = Query(None, description="Filtrar por docente específico"),
    curso_id: Optional[int] = Query(None, description="Filtrar por curso específico")
):
    """Obtener todas las calificaciones del estudiante con filtros opcionales"""
    
    try:
        # Obtener matrículas activas del estudiante
        matriculas_query = db.query(Matricula).filter(
            Matricula.estudiante_id == current_user.id,
            Matricula.is_active == True
        )
        
        # Aplicar filtros
        if ciclo_id:
            matriculas_query = matriculas_query.filter(Matricula.ciclo_id == ciclo_id)
        
        matriculas_activas = matriculas_query.all()
        
        # Obtener cursos de los ciclos en los que está matriculado
        ciclo_ids = [matricula.ciclo_id for matricula in matriculas_activas]
        
        if not ciclo_ids:
            return []
        
        # Query para obtener notas
        notas_query = db.query(Nota).join(Curso).join(Ciclo).filter(
            Nota.estudiante_id == current_user.id,
            Curso.ciclo_id.in_(ciclo_ids)
        ).options(
            joinedload(Nota.curso).joinedload(Curso.docente),
            joinedload(Nota.curso).joinedload(Curso.ciclo).joinedload(Ciclo.carrera)
        )
        
        # Aplicar filtros adicionales
        if docente_id:
            notas_query = notas_query.filter(Curso.docente_id == docente_id)
        
        if curso_id:
            notas_query = notas_query.filter(Nota.curso_id == curso_id)
        
        notas = notas_query.all()
        
        # Convertir a formato de respuesta
        notas_response = []
        for nota in notas:
            # Calcular promedio usando GradeCalculator
            promedio = GradeCalculator.calcular_promedio_nota(nota)
            
            nota_data = {
                "id": nota.id,
                "curso_id": nota.curso_id,
                "curso_nombre": nota.curso.nombre,
                "docente_id": nota.curso.docente_id,
                "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}",
                "ciclo_id": nota.curso.ciclo_id,
                "ciclo_nombre": nota.curso.ciclo.nombre,
                "ciclo_año": nota.curso.ciclo.año,
                "carrera_nombre": nota.curso.ciclo.carrera.nombre if nota.curso.ciclo.carrera else None,
                
                # Evaluaciones semanales
                "evaluacion1": float(nota.evaluacion1) if nota.evaluacion1 is not None else None,
                "evaluacion2": float(nota.evaluacion2) if nota.evaluacion2 is not None else None,
                "evaluacion3": float(nota.evaluacion3) if nota.evaluacion3 is not None else None,
                "evaluacion4": float(nota.evaluacion4) if nota.evaluacion4 is not None else None,
                "evaluacion5": float(nota.evaluacion5) if nota.evaluacion5 is not None else None,
                "evaluacion6": float(nota.evaluacion6) if nota.evaluacion6 is not None else None,
                "evaluacion7": float(nota.evaluacion7) if nota.evaluacion7 is not None else None,
                "evaluacion8": float(nota.evaluacion8) if nota.evaluacion8 is not None else None,
                
                # Prácticas
                "practica1": float(nota.practica1) if nota.practica1 is not None else None,
                "practica2": float(nota.practica2) if nota.practica2 is not None else None,
                "practica3": float(nota.practica3) if nota.practica3 is not None else None,
                "practica4": float(nota.practica4) if nota.practica4 is not None else None,
                
                # Parciales
                "parcial1": float(nota.parcial1) if nota.parcial1 is not None else None,
                "parcial2": float(nota.parcial2) if nota.parcial2 is not None else None,
                
                # Promedio calculado
                "promedio_final": float(promedio) if promedio is not None else None,
                
                # Fechas
                "created_at": nota.created_at,
                "updated_at": nota.updated_at
            }
            
            notas_response.append(nota_data)
        
        return notas_response
        
    except Exception as e:
        print(f"Error in get_student_grades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las calificaciones del estudiante"
        )

@router.get("/grades/filters")
def get_student_grades_filters(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener filtros disponibles para las calificaciones del estudiante - solo ciclos basados en matrículas"""
    
    try:
        # Obtener matrículas activas del estudiante
        matriculas_activas = db.query(Matricula).filter(
            Matricula.estudiante_id == current_user.id,
            Matricula.is_active == True
        ).all()
        
        # Obtener cursos de los ciclos en los que está matriculado
        ciclo_ids = [matricula.ciclo_id for matricula in matriculas_activas]
        
        if not ciclo_ids:
            return {
                "ciclos": [],
                "docentes": []
            }
        
        # Obtener ciclos únicos ordenados del primero al más alto (por número de ciclo)
        ciclos = db.query(Ciclo).filter(
            Ciclo.id.in_(ciclo_ids),
            Ciclo.is_active == True
        ).order_by(Ciclo.numero.asc()).all()
        
        # Obtener docentes únicos de los cursos del estudiante
        docentes = db.query(User).join(Curso).filter(
            Curso.ciclo_id.in_(ciclo_ids),
            Curso.is_active == True,
            User.role == "docente"
        ).distinct().order_by(User.first_name, User.last_name).all()
        
        return {
            "ciclos": [
                {
                    "id": ciclo.id,
                    "nombre": ciclo.nombre,
                    "año": ciclo.año,
                    "numero": ciclo.numero
                }
                for ciclo in ciclos
            ],
            "docentes": [
                {
                    "id": docente.id,
                    "nombre": f"{docente.first_name} {docente.last_name}"
                }
                for docente in docentes
            ]
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
    ciclo_id: Optional[int] = Query(None, description="Filtrar por ciclo específico"),
    docente_id: Optional[int] = Query(None, description="Filtrar por docente específico")
):
    """Obtener estadísticas de calificaciones del estudiante"""
    
    try:
        # Obtener matrículas activas del estudiante
        matriculas_query = db.query(Matricula).filter(
            Matricula.estudiante_id == current_user.id,
            Matricula.is_active == True
        )
        
        # Aplicar filtros
        if ciclo_id:
            matriculas_query = matriculas_query.filter(Matricula.ciclo_id == ciclo_id)
        
        matriculas_activas = matriculas_query.all()
        
        # Obtener cursos de los ciclos en los que está matriculado
        ciclo_ids = [matricula.ciclo_id for matricula in matriculas_activas]
        
        if not ciclo_ids:
            return {
                "total_cursos": 0,
                "promedio_general": 0,
                "cursos_aprobados": 0,
                "cursos_desaprobados": 0,
                "cursos_pendientes": 0
            }
        
        # Query para obtener notas
        notas_query = db.query(Nota).join(Curso).filter(
            Nota.estudiante_id == current_user.id,
            Curso.ciclo_id.in_(ciclo_ids)
        )
        
        # Aplicar filtros adicionales
        if docente_id:
            notas_query = notas_query.filter(Curso.docente_id == docente_id)
        
        notas = notas_query.all()
        
        # Calcular estadísticas
        total_cursos = len(notas)
        cursos_aprobados = 0
        cursos_desaprobados = 0
        cursos_pendientes = 0
        promedios_validos = []
        
        for nota in notas:
            promedio = GradeCalculator.calcular_promedio_nota(nota)
            
            if promedio is not None:
                promedios_validos.append(float(promedio))
                if float(promedio) >= 13:
                    cursos_aprobados += 1
                else:
                    cursos_desaprobados += 1
            else:
                cursos_pendientes += 1
        
        # Calcular promedio general
        promedio_general = 0
        if promedios_validos:
            promedio_general = sum(promedios_validos) / len(promedios_validos)
        
        # Calcular créditos completados (asumiendo 3 créditos por curso aprobado)
        creditos_completados = cursos_aprobados * 3
        
        return {
            "total_cursos": total_cursos,
            "promedio_general": round(promedio_general, 2),
            "cursos_aprobados": cursos_aprobados,
            "cursos_desaprobados": cursos_desaprobados,
            "creditos_completados": creditos_completados
        }
        
    except Exception as e:
        print(f"Error in get_student_grades_statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las estadísticas de calificaciones"
        )

@router.get("/academic-performance-no-auth")
def get_academic_performance_no_auth():
    """Endpoint de prueba sin autenticación"""
    
    print(f"=== ENDPOINT SIN AUTENTICACIÓN EJECUTÁNDOSE ===")
    
    return {
        "message": "Endpoint sin autenticación funcionando",
        "status": "OK"
    }

@router.get("/academic-performance-test")
def get_academic_performance_test(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Endpoint de prueba para verificar si el problema está en la validación"""
    
    print(f"=== ENDPOINT DE PRUEBA EJECUTÁNDOSE ===")
    print(f"Usuario: {current_user.id}, DNI: {current_user.dni}")
    
    return {
        "message": "Endpoint de prueba funcionando",
        "user_id": current_user.id,
        "user_dni": current_user.dni
    }

@router.get("/academic-performance", response_model=List[RendimientoAcademicoCiclo])
def get_academic_performance(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener el rendimiento académico del estudiante por ciclos"""
    
    try:
        print(f"=== INICIO ENDPOINT ACADEMIC PERFORMANCE ===")
        print(f"Usuario autenticado: {current_user.id}, DNI: {current_user.dni}, Rol: {current_user.role}")
        
        # Obtener todas las matrículas del estudiante con información del ciclo
        matriculas = db.query(Matricula).options(
            joinedload(Matricula.ciclo)
        ).filter(
            Matricula.estudiante_id == current_user.id,
            Matricula.is_active == True
        ).all()
        
        print(f"Matrículas encontradas: {len(matriculas)}")
        
        if not matriculas:
            print("No se encontraron matrículas para el estudiante")
            return []
        
        performance_data = []
        
        for matricula in matriculas:
            print(f"Procesando matrícula para ciclo: {matricula.ciclo.nombre}")
            
            # Obtener todos los cursos del ciclo
            cursos_ciclo = db.query(Curso).filter(
                Curso.ciclo_id == matricula.ciclo_id,
                Curso.is_active == True
            ).all()
            
            print(f"Cursos en el ciclo {matricula.ciclo.nombre}: {len(cursos_ciclo)}")
            
            # Obtener las notas del estudiante para los cursos de este ciclo
            notas_ciclo = db.query(Nota).options(
                joinedload(Nota.curso)
            ).filter(
                Nota.estudiante_id == current_user.id,
                Nota.curso_id.in_([curso.id for curso in cursos_ciclo]) if cursos_ciclo else []
            ).all()
            
            print(f"Notas encontradas para el ciclo {matricula.ciclo.nombre}: {len(notas_ciclo)}")
            
            # Calcular promedio del ciclo usando GradeCalculator
            calculator = GradeCalculator()
            total_promedio = 0
            cursos_con_notas = 0
            
            for nota in notas_ciclo:
                try:
                    promedio_curso = calculator.calculate_final_grade(nota)
                    print(f"Promedio del curso {nota.curso.nombre}: {promedio_curso}")
                    if promedio_curso is not None:
                        total_promedio += float(promedio_curso)
                        cursos_con_notas += 1
                except Exception as e:
                    print(f"Error calculando promedio para curso {nota.curso.nombre}: {e}")
                    continue
            
            # Calcular promedio del ciclo
            promedio_ciclo = total_promedio / cursos_con_notas if cursos_con_notas > 0 else 0.0
            
            print(f"Promedio final del ciclo {matricula.ciclo.nombre}: {promedio_ciclo}")
            
            # Crear el objeto de datos de rendimiento
            ciclo_data = {
                "ciclo_id": matricula.ciclo.id,
                "ciclo_nombre": matricula.ciclo.nombre,
                "ciclo_numero": matricula.ciclo.numero,
                "promedio_ciclo": round(promedio_ciclo, 2),
                "numero_cursos": len(cursos_ciclo),
                "fecha_matricula": matricula.fecha_matricula.isoformat() if matricula.fecha_matricula else None
            }
            
            print(f"Datos del ciclo creados: {ciclo_data}")
            performance_data.append(ciclo_data)
        
        # Ordenar por número de ciclo
        performance_data.sort(key=lambda x: x["ciclo_numero"])
        
        print(f"Datos de rendimiento final: {performance_data}")
        print(f"=== FIN ENDPOINT ACADEMIC PERFORMANCE ===")
        
        return performance_data
        
    except Exception as e:
        print(f"ERROR CRÍTICO en get_academic_performance: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el rendimiento académico: {str(e)}"
        )

@router.get("/grades/{curso_id}", response_model=List[NotaEstudianteResponse])
def get_student_grades_by_course(
    curso_id: int,
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener calificaciones del estudiante para un curso específico"""
    
    try:
        # Verificar que el estudiante esté matriculado en el curso
        matricula = db.query(Matricula).join(Curso).filter(
            Matricula.estudiante_id == current_user.id,
            Curso.id == curso_id,
            Matricula.is_active == True
        ).first()
        
        if not matricula:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No estás matriculado en este curso"
            )
        
        # Obtener notas del curso
        nota = db.query(Nota).filter(
            Nota.estudiante_id == current_user.id,
            Nota.curso_id == curso_id
        ).options(
            joinedload(Nota.curso).joinedload(Curso.docente),
            joinedload(Nota.curso).joinedload(Curso.ciclo).joinedload(Ciclo.carrera)
        ).first()
        
        if not nota:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontraron calificaciones para este curso"
            )
        
        # Calcular promedio usando GradeCalculator
        promedio = GradeCalculator.calcular_promedio_nota(nota)
        
        nota_data = {
            "id": nota.id,
            "curso_id": nota.curso_id,
            "curso_nombre": nota.curso.nombre,
            "docente_id": nota.curso.docente_id,
            "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}",
            "ciclo_id": nota.curso.ciclo_id,
            "ciclo_nombre": nota.curso.ciclo.nombre,
            "ciclo_año": nota.curso.ciclo.año,
            "carrera_nombre": nota.curso.ciclo.carrera.nombre if nota.curso.ciclo.carrera else None,
            
            # Evaluaciones semanales
            "evaluacion1": float(nota.evaluacion1) if nota.evaluacion1 is not None else None,
            "evaluacion2": float(nota.evaluacion2) if nota.evaluacion2 is not None else None,
            "evaluacion3": float(nota.evaluacion3) if nota.evaluacion3 is not None else None,
            "evaluacion4": float(nota.evaluacion4) if nota.evaluacion4 is not None else None,
            "evaluacion5": float(nota.evaluacion5) if nota.evaluacion5 is not None else None,
            "evaluacion6": float(nota.evaluacion6) if nota.evaluacion6 is not None else None,
            "evaluacion7": float(nota.evaluacion7) if nota.evaluacion7 is not None else None,
            "evaluacion8": float(nota.evaluacion8) if nota.evaluacion8 is not None else None,
            
            # Prácticas
            "practica1": float(nota.practica1) if nota.practica1 is not None else None,
            "practica2": float(nota.practica2) if nota.practica2 is not None else None,
            "practica3": float(nota.practica3) if nota.practica3 is not None else None,
            "practica4": float(nota.practica4) if nota.practica4 is not None else None,
            
            # Parciales
            "parcial1": float(nota.parcial1) if nota.parcial1 is not None else None,
            "parcial2": float(nota.parcial2) if nota.parcial2 is not None else None,
            
            # Promedio calculado
            "promedio_final": float(promedio) if promedio is not None else None,
            
            # Fechas
            "created_at": nota.created_at,
            "updated_at": nota.updated_at
        }
        
        return [nota_data]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_student_grades_by_course: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las calificaciones del curso"
        )

@router.get("/final-grades", response_model=List[PromedioFinalEstudianteResponse])
def get_student_final_grades(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db),
    ciclo_id: Optional[int] = Query(None, description="Filtrar por ciclo específico")
):
    """Obtener promedios finales del estudiante por curso"""
    
    try:
        # Obtener matrículas activas del estudiante
        matriculas_query = db.query(Matricula).filter(
            Matricula.estudiante_id == current_user.id,
            Matricula.is_active == True
        )
        
        # Aplicar filtros
        if ciclo_id:
            matriculas_query = matriculas_query.filter(Matricula.ciclo_id == ciclo_id)
        
        matriculas_activas = matriculas_query.all()
        
        # Obtener cursos de los ciclos en los que está matriculado
        ciclo_ids = [matricula.ciclo_id for matricula in matriculas_activas]
        
        if not ciclo_ids:
            return []
        
        # Obtener notas
        notas = db.query(Nota).join(Curso).filter(
            Nota.estudiante_id == current_user.id,
            Curso.ciclo_id.in_(ciclo_ids)
        ).options(
            joinedload(Nota.curso).joinedload(Curso.docente),
            joinedload(Nota.curso).joinedload(Curso.ciclo)
        ).all()
        
        # Convertir a formato de respuesta
        promedios_response = []
        for nota in notas:
            promedio = GradeCalculator.calcular_promedio_nota(nota)
            
            promedio_data = {
                "curso_id": nota.curso_id,
                "curso_nombre": nota.curso.nombre,
                "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}",
                "ciclo_nombre": nota.curso.ciclo.nombre,
                "promedio_final": float(promedio) if promedio is not None else None,
                "estado": "APROBADO" if promedio and float(promedio) >= 13 else "DESAPROBADO" if promedio else "PENDIENTE"
            }
            
            promedios_response.append(promedio_data)
        
        return promedios_response
        
    except Exception as e:
        print(f"Error in get_student_final_grades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener los promedios finales"
        )

@router.get("/final-grades/{curso_id}", response_model=PromedioFinalEstudianteResponse)
def get_student_final_grade_by_course(
    curso_id: int,
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener promedio final del estudiante para un curso específico"""
    
    try:
        # Verificar que el estudiante esté matriculado en el curso
        matricula = db.query(Matricula).join(Curso).filter(
            Matricula.estudiante_id == current_user.id,
            Curso.id == curso_id,
            Matricula.is_active == True
        ).first()
        
        if not matricula:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No estás matriculado en este curso"
            )
        
        # Obtener nota del curso
        nota = db.query(Nota).filter(
            Nota.estudiante_id == current_user.id,
            Nota.curso_id == curso_id
        ).options(
            joinedload(Nota.curso).joinedload(Curso.docente),
            joinedload(Nota.curso).joinedload(Curso.ciclo)
        ).first()
        
        if not nota:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontraron calificaciones para este curso"
            )
        
        # Calcular promedio
        promedio = GradeCalculator.calcular_promedio_nota(nota)
        
        return {
            "curso_id": nota.curso_id,
            "curso_nombre": nota.curso.nombre,
            "docente_nombre": f"{nota.curso.docente.first_name} {nota.curso.docente.last_name}",
            "ciclo_nombre": nota.curso.ciclo.nombre,
            "promedio_final": float(promedio) if promedio is not None else None,
            "estado": "APROBADO" if promedio and float(promedio) >= 13 else "DESAPROBADO" if promedio else "PENDIENTE"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_student_final_grade_by_course: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el promedio final del curso"
        )

@router.get("/grades-by-type/{curso_id}", response_model=NotasPorTipoResponse)
def get_student_grades_by_type(
    curso_id: int,
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener calificaciones del estudiante agrupadas por tipo (evaluaciones, prácticas, parciales)"""
    
    try:
        # Verificar que el estudiante esté matriculado en el curso
        matricula = db.query(Matricula).join(Curso).filter(
            Matricula.estudiante_id == current_user.id,
            Curso.id == curso_id,
            Matricula.is_active == True
        ).first()
        
        if not matricula:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No estás matriculado en este curso"
            )
        
        # Obtener nota del curso
        nota = db.query(Nota).filter(
            Nota.estudiante_id == current_user.id,
            Nota.curso_id == curso_id
        ).options(
            joinedload(Nota.curso)
        ).first()
        
        if not nota:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontraron calificaciones para este curso"
            )
        
        # Agrupar notas por tipo
        evaluaciones = []
        for i in range(1, 9):
            eval_attr = f"evaluacion{i}"
            eval_value = getattr(nota, eval_attr)
            if eval_value is not None:
                evaluaciones.append({
                    "numero": i,
                    "nota": float(eval_value),
                    "tipo": f"Evaluación {i}"
                })
        
        practicas = []
        for i in range(1, 5):
            prac_attr = f"practica{i}"
            prac_value = getattr(nota, prac_attr)
            if prac_value is not None:
                practicas.append({
                    "numero": i,
                    "nota": float(prac_value),
                    "tipo": f"Práctica {i}"
                })
        
        parciales = []
        for i in range(1, 3):
            parc_attr = f"parcial{i}"
            parc_value = getattr(nota, parc_attr)
            if parc_value is not None:
                parciales.append({
                    "numero": i,
                    "nota": float(parc_value),
                    "tipo": f"Parcial {i}"
                })
        
        # Calcular promedio final
        promedio_final = GradeCalculator.calcular_promedio_nota(nota)
        
        return {
            "curso_id": curso_id,
            "curso_nombre": nota.curso.nombre,
            "evaluaciones": evaluaciones,
            "practicas": practicas,
            "parciales": parciales,
            "promedio_final": float(promedio_final) if promedio_final is not None else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_student_grades_by_type: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las calificaciones por tipo"
        )

@router.get("/courses-with-grades", response_model=List[CursoConNotasResponse])
def get_student_courses_with_grades(
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db),
    ciclo_id: Optional[int] = Query(None, description="Filtrar por ciclo específico")
):
    """Obtener cursos del estudiante con sus respectivas calificaciones"""
    
    try:
        # Obtener matrículas activas del estudiante
        matriculas_query = db.query(Matricula).filter(
            Matricula.estudiante_id == current_user.id,
            Matricula.is_active == True
        )
        
        # Aplicar filtros
        if ciclo_id:
            matriculas_query = matriculas_query.filter(Matricula.ciclo_id == ciclo_id)
        
        matriculas_activas = matriculas_query.all()
        
        # Obtener cursos de los ciclos en los que está matriculado
        ciclo_ids = [matricula.ciclo_id for matricula in matriculas_activas]
        
        if not ciclo_ids:
            return []
        
        # Obtener cursos con notas
        cursos = db.query(Curso).filter(
            Curso.ciclo_id.in_(ciclo_ids),
            Curso.is_active == True
        ).options(
            joinedload(Curso.ciclo),
            joinedload(Curso.docente)
        ).all()
        
        # Convertir a formato de respuesta
        cursos_response = []
        for curso in cursos:
            # Obtener nota del estudiante para este curso
            nota = db.query(Nota).filter(
                Nota.estudiante_id == current_user.id,
                Nota.curso_id == curso.id
            ).first()
            
            # Calcular promedio si existe la nota
            promedio_final = None
            if nota:
                promedio_final = GradeCalculator.calcular_promedio_nota(nota)
            
            curso_data = {
                "id": curso.id,
                "nombre": curso.nombre,
                "docente_nombre": f"{curso.docente.first_name} {curso.docente.last_name}",
                "ciclo_nombre": curso.ciclo.nombre,
                "ciclo_año": curso.ciclo.año,
                "promedio_final": float(promedio_final) if promedio_final is not None else None,
                "estado": "APROBADO" if promedio_final and float(promedio_final) >= 13 else "DESAPROBADO" if promedio_final else "PENDIENTE",
                "tiene_notas": nota is not None
            }
            
            cursos_response.append(curso_data)
        
        return cursos_response
        
    except Exception as e:
        print(f"Error in get_student_courses_with_grades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener los cursos con calificaciones"
        )

@router.get("/courses/{curso_id}/evaluation-descriptions/{tipo_evaluacion}")
def get_evaluation_description(
    curso_id: int,
    tipo_evaluacion: str,
    current_user: User = Depends(get_estudiante_user),
    db: Session = Depends(get_db)
):
    """Obtener la descripción de una evaluación específica para un estudiante"""
    
    try:
        # Verificar que el estudiante tenga notas en el curso (lo que indica que está matriculado)
        nota_estudiante = db.query(Nota).filter(
            Nota.estudiante_id == current_user.id,
            Nota.curso_id == curso_id
        ).first()
        
        if not nota_estudiante:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tienes acceso a este curso o el curso no existe"
            )
        
        # Obtener la descripción de la evaluación
        descripcion = db.query(DescripcionEvaluacion).filter(
            DescripcionEvaluacion.curso_id == curso_id,
            DescripcionEvaluacion.tipo_evaluacion == tipo_evaluacion
        ).first()
        
        if not descripcion:
            # Si no hay descripción, devolver información básica
            return {
                "id": None,
                "curso_id": curso_id,
                "tipo_evaluacion": tipo_evaluacion,
                "descripcion": "Sin descripción disponible",
                "fecha_evaluacion": None,
                "created_at": None,
                "updated_at": None
            }
        
        return {
            "id": descripcion.id,
            "curso_id": descripcion.curso_id,
            "tipo_evaluacion": descripcion.tipo_evaluacion,
            "descripcion": descripcion.descripcion,
            "fecha_evaluacion": descripcion.fecha_evaluacion.isoformat() if descripcion.fecha_evaluacion else None,
            "created_at": descripcion.created_at.isoformat() if descripcion.created_at else None,
            "updated_at": descripcion.updated_at.isoformat() if descripcion.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_evaluation_description: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener la descripción de la evaluación"
        )