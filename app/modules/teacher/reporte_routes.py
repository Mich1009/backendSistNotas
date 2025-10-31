from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, extract
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal

from ...database import get_db
from ..auth.dependencies import get_docente_user
from ..auth.models import User, RoleEnum
from .models import Carrera, Ciclo, Curso, Matricula, Nota
from .schemas import (
    ReporteRendimientoResponse, ResumenReporteResponse, 
    CursoReporteResponse, EstudianteRendimientoResponse
)

router = APIRouter()

@router.get("/reports/performance", response_model=Dict[str, Any])
def get_performance_report(
    año: Optional[int] = Query(None, description="Año para filtrar los cursos"),
    ciclo_id: Optional[int] = Query(None, description="ID del ciclo para filtrar"),
    curso_nombre: Optional[str] = Query(None, description="Nombre del curso para buscar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_docente_user)
):
    """
    Obtener reporte de rendimiento de estudiantes por curso
    """
    try:
        # Query base para cursos del docente
        cursos_query = db.query(Curso).filter(
            Curso.docente_id == current_user.id,
            Curso.is_active == True
        )
        
        # Aplicar filtros
        if año:
            cursos_query = cursos_query.join(Ciclo).filter(
                Ciclo.año == año
            )
        
        if ciclo_id:
            cursos_query = cursos_query.filter(Curso.ciclo_id == ciclo_id)
            
        if curso_nombre:
            cursos_query = cursos_query.filter(
                Curso.nombre.ilike(f"%{curso_nombre}%")
            )
        
        cursos = cursos_query.all()
        
        # Obtener datos de rendimiento por curso
        cursos_data = []
        total_estudiantes = 0
        suma_promedios = 0
        estudiantes_aprobados = 0
        
        for curso in cursos:
            # Obtener estudiantes matriculados en el curso
            matriculas = db.query(Matricula).filter(
                Matricula.ciclo_id == curso.ciclo_id,
                Matricula.is_active == True
            ).all()
            
            estudiantes_curso = []
            curso_suma_promedios = 0
            curso_estudiantes_aprobados = 0
            curso_total_estudiantes = 0
            
            for matricula in matriculas:
                # Obtener notas del estudiante en este curso
                notas = db.query(Nota).filter(
                    Nota.estudiante_id == matricula.estudiante_id,
                    Nota.curso_id == curso.id
                ).all()
                
                if notas:
                    estudiante = matricula.estudiante
                    
                    # Calcular promedio ponderado del estudiante con pesos correctos
                    # PESOS CORRECTOS: Evaluaciones 10%, Prácticas 30%, Parciales 60%
                    peso_evaluaciones = 0.1
                    peso_practicas = 0.3
                    peso_parciales = 0.6
                    
                    promedio_evaluaciones = 0
                    promedio_practicas = 0
                    promedio_parciales = 0
                    
                    suma_pesos = 0
                    tiene_evaluaciones = False
                    tiene_practicas = False
                    tiene_parciales = False
                    
                    # Tomar la primera (y debería ser única) nota del estudiante para este curso
                    nota = notas[0]
                    
                    # Calcular promedio de evaluaciones (1-8)
                    evaluaciones = []
                    for i in range(1, 9):
                        eval_val = getattr(nota, f'evaluacion{i}')
                        if eval_val is not None and float(eval_val) > 0:
                            evaluaciones.append(float(eval_val))
                    
                    if evaluaciones:
                        promedio_evaluaciones = sum(evaluaciones) / len(evaluaciones)
                        suma_pesos += peso_evaluaciones
                        tiene_evaluaciones = True
                    
                    # Calcular promedio de prácticas (1-4)
                    practicas = []
                    for i in range(1, 5):
                        prac_val = getattr(nota, f'practica{i}')
                        if prac_val is not None and float(prac_val) > 0:
                            practicas.append(float(prac_val))
                    
                    if practicas:
                        promedio_practicas = sum(practicas) / len(practicas)
                        suma_pesos += peso_practicas
                        tiene_practicas = True
                    
                    # Calcular promedio de parciales (1-2)
                    parciales = []
                    for i in range(1, 3):
                        parc_val = getattr(nota, f'parcial{i}')
                        if parc_val is not None and float(parc_val) > 0:
                            parciales.append(float(parc_val))
                    
                    if parciales:
                        promedio_parciales = sum(parciales) / len(parciales)
                        suma_pesos += peso_parciales
                        tiene_parciales = True
                    
                    # Calcular promedio ponderado final
                    if suma_pesos > 0:
                        promedio_final = (
                            promedio_evaluaciones * peso_evaluaciones +
                            promedio_practicas * peso_practicas +
                            promedio_parciales * peso_parciales
                        ) / suma_pesos
                    else:
                        promedio_final = 0
                    
                    estado = "Aprobado" if promedio_final >= 13.0 else "Reprobado"
                    
                    estudiante_data = {
                        "id": estudiante.id,
                        "nombre": f"{estudiante.first_name} {estudiante.last_name}",
                        "dni": estudiante.dni,
                        "email": estudiante.email,
                        "promedio_final": round(promedio_final, 2),
                        "estado": estado
                    }
                    
                    estudiantes_curso.append(estudiante_data)
                    curso_suma_promedios += promedio_final
                    curso_total_estudiantes += 1
                    
                    if estado == "Aprobado":
                        curso_estudiantes_aprobados += 1
            
            # Calcular estadísticas del curso
            promedio_curso = curso_suma_promedios / curso_total_estudiantes if curso_total_estudiantes > 0 else 0
            tasa_aprobacion = (curso_estudiantes_aprobados / curso_total_estudiantes * 100) if curso_total_estudiantes > 0 else 0
            
            curso_data = {
                "id": curso.id,
                "nombre": curso.nombre,
                "ciclo": {
                    "id": curso.ciclo.id if curso.ciclo else None,
                    "nombre": curso.ciclo.nombre if curso.ciclo else "Sin ciclo",
                    "año": curso.ciclo.año if curso.ciclo else None
                },
                "total_estudiantes": curso_total_estudiantes,
                "estudiantes_aprobados": curso_estudiantes_aprobados,
                "estudiantes_reprobados": curso_total_estudiantes - curso_estudiantes_aprobados,
                "promedio_curso": round(promedio_curso, 2),
                "tasa_aprobacion": round(tasa_aprobacion, 2),
                "estudiantes": estudiantes_curso
            }
            
            cursos_data.append(curso_data)
            
            # Acumular para estadísticas generales
            total_estudiantes += curso_total_estudiantes
            suma_promedios += curso_suma_promedios
            estudiantes_aprobados += curso_estudiantes_aprobados
        
        # Calcular estadísticas generales
        # El promedio general debe ser el promedio de los promedios de curso, no de estudiantes individuales
        promedio_general = 0
        if len(cursos_data) > 0:
            suma_promedios_cursos = sum(curso["promedio_curso"] for curso in cursos_data if curso["promedio_curso"] > 0)
            cursos_con_promedio = len([curso for curso in cursos_data if curso["promedio_curso"] > 0])
            promedio_general = suma_promedios_cursos / cursos_con_promedio if cursos_con_promedio > 0 else 0
        
        tasa_aprobacion_general = (estudiantes_aprobados / total_estudiantes * 100) if total_estudiantes > 0 else 0
        
        resumen = {
            "total_cursos": len(cursos),
            "total_estudiantes": total_estudiantes,
            "promedio_general": round(promedio_general, 2),
            "tasa_aprobacion": round(tasa_aprobacion_general, 2),
            "estudiantes_aprobados": estudiantes_aprobados,
            "estudiantes_reprobados": total_estudiantes - estudiantes_aprobados
        }
        
        return {
            "resumen": resumen,
            "cursos": cursos_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar el reporte: {str(e)}"
        )

@router.get("/reports/years", response_model=List[int])
def get_available_years(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_docente_user)
):
    """
    Obtener años disponibles para filtrar reportes
    """
    try:
        # Obtener años únicos de los ciclos donde el docente tiene cursos
        años = db.query(Ciclo.año).join(Curso).filter(
            Curso.docente_id == current_user.id,
            Curso.is_active == True,
            Ciclo.año.isnot(None)
        ).distinct().order_by(Ciclo.año.desc()).all()
        
        return [año[0] for año in años if año[0]]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener años disponibles: {str(e)}"
        )

@router.get("/reports/cycles", response_model=List[Dict[str, Any]])
def get_available_cycles(
    año: Optional[int] = Query(None, description="Año para filtrar ciclos"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_docente_user)
):
    """
    Obtener ciclos disponibles para filtrar reportes
    """
    try:
        # Query base para ciclos donde el docente tiene cursos
        ciclos_query = db.query(Ciclo).join(Curso).filter(
            Curso.docente_id == current_user.id,
            Curso.is_active == True,
            Ciclo.is_active == True
        )
        
        # Filtrar por año si se proporciona
        if año:
            ciclos_query = ciclos_query.filter(Ciclo.año == año)
        
        ciclos = ciclos_query.distinct().order_by(Ciclo.año.desc(), Ciclo.nombre).all()
        
        ciclos_data = []
        for ciclo in ciclos:
            ciclos_data.append({
                "id": ciclo.id,
                "nombre": ciclo.nombre,
                "año": ciclo.año,
                "fecha_inicio": ciclo.fecha_inicio.isoformat() if ciclo.fecha_inicio else None,
                "fecha_fin": ciclo.fecha_fin.isoformat() if ciclo.fecha_fin else None
            })
        
        return ciclos_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener cursos disponibles: {str(e)}"
        )

@router.get("/reports/failed-students/{curso_id}", response_model=Dict[str, List[Dict[str, Any]]])
def get_failed_students_by_course(
    curso_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_docente_user)
):
    """
    Obtener estudiantes desaprobados de un curso específico con sus promedios calculados
    """
    try:
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
        matriculas = db.query(Matricula).options(
            joinedload(Matricula.estudiante)
        ).filter(
            Matricula.ciclo_id == curso.ciclo_id,
            Matricula.is_active == True
        ).all()
        
        estudiantes_desaprobados = []
        
        for matricula in matriculas:
            # Obtener notas del estudiante en este curso específico
            notas = db.query(Nota).filter(
                Nota.estudiante_id == matricula.estudiante_id,
                Nota.curso_id == curso_id
            ).all()
            if notas:
                estudiante = matricula.estudiante
                
                # Calcular promedio ponderado del estudiante con pesos correctos
                # PESOS CORRECTOS: Evaluaciones 10%, Prácticas 30%, Parciales 60%
                peso_evaluaciones = 0.1
                peso_practicas = 0.3
                peso_parciales = 0.6
                
                promedio_evaluaciones = 0
                promedio_practicas = 0
                promedio_parciales = 0
                
                suma_pesos = 0
                
                # Tomar la primera (y debería ser única) nota del estudiante para este curso
                nota = notas[0]
                
                # Calcular promedio de evaluaciones (1-8)
                evaluaciones = []
                for i in range(1, 9):
                    eval_val = getattr(nota, f'evaluacion{i}')
                    if eval_val is not None and float(eval_val) > 0:
                        evaluaciones.append(float(eval_val))
                
                if evaluaciones:
                    promedio_evaluaciones = sum(evaluaciones) / len(evaluaciones)
                    suma_pesos += peso_evaluaciones
                
                # Calcular promedio de prácticas (1-4)
                practicas = []
                for i in range(1, 5):
                    prac_val = getattr(nota, f'practica{i}')
                    if prac_val is not None and float(prac_val) > 0:
                        practicas.append(float(prac_val))
                
                if practicas:
                    promedio_practicas = sum(practicas) / len(practicas)
                    suma_pesos += peso_practicas
                
                # Calcular promedio de parciales (1-2)
                parciales = []
                for i in range(1, 3):
                    parc_val = getattr(nota, f'parcial{i}')
                    if parc_val is not None and float(parc_val) > 0:
                        parciales.append(float(parc_val))
                
                if parciales:
                    promedio_parciales = sum(parciales) / len(parciales)
                    suma_pesos += peso_parciales
                
                # Calcular promedio ponderado final
                promedio_final = 0
                if suma_pesos > 0:
                    promedio_final = (
                        (promedio_evaluaciones * peso_evaluaciones) +
                        (promedio_practicas * peso_practicas) +
                        (promedio_parciales * peso_parciales)
                    ) / suma_pesos
                
                # Solo incluir estudiantes desaprobados (promedio < 13.0)
                if promedio_final < 13.0:
                    estudiantes_desaprobados.append({
                        "id": estudiante.id,
                        "dni": estudiante.dni,
                        "nombre": estudiante.first_name,
                        "apellido": estudiante.last_name,
                        "promedio_final": round(promedio_final, 2),
                        "promedio_evaluaciones": round(promedio_evaluaciones, 2) if evaluaciones else None,
                        "promedio_practicas": round(promedio_practicas, 2) if practicas else None,
                        "promedio_parciales": round(promedio_parciales, 2) if parciales else None
                    })
        
        # Ordenar por promedio final (de menor a mayor)
        estudiantes_desaprobados.sort(key=lambda x: x["promedio_final"])
        
        return {"estudiantes": estudiantes_desaprobados}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estudiantes desaprobados: {str(e)}"
        )

@router.get("/reports/courses", response_model=List[Dict[str, Any]])
def get_courses_for_reports(
    año: Optional[int] = Query(None, description="Año para filtrar cursos"),
    ciclo_id: Optional[int] = Query(None, description="ID del ciclo para filtrar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_docente_user)
):
    """
    Obtener cursos disponibles para reportes
    """
    try:
        # Query base para cursos del docente
        cursos_query = db.query(Curso).filter(
            Curso.docente_id == current_user.id,
            Curso.is_active == True
        )
        
        # Aplicar filtros
        if año or ciclo_id:
            cursos_query = cursos_query.join(Ciclo)
            
            if año:
                cursos_query = cursos_query.filter(Ciclo.año == año)
            
            if ciclo_id:
                cursos_query = cursos_query.filter(Ciclo.id == ciclo_id)
        
        cursos = cursos_query.order_by(Curso.nombre).all()
        
        cursos_data = []
        for curso in cursos:
            cursos_data.append({
                "id": curso.id,
                "nombre": curso.nombre,
                "ciclo": {
                    "id": curso.ciclo.id if curso.ciclo else None,
                    "nombre": curso.ciclo.nombre if curso.ciclo else "Sin ciclo",
                    "año": curso.ciclo.año if curso.ciclo else None
                }
            })
        
        return cursos_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener cursos: {str(e)}"
        )