from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc, asc
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import json

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ...shared.models import User, RoleEnum, Carrera, Ciclo, Curso, Matricula, Nota, HistorialNota
from ...shared.grade_calculator import GradeCalculator
from .schemas import (
    ReporteUsuarios, ReporteAcademico, EstadisticasGenerales
)

router = APIRouter(prefix="/reportes", tags=["Admin - Reportes"])

# ==================== VISTA DE REPORTES DINAMICOS ====================

@router.get("/jerarquicos/carreras-ciclos")
async def get_estructura_jerarquica(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    año: Optional[int] = Query(None, description="Filtrar por año específico")
):
    """
    Obtiene la estructura jerárquica completa: Carreras -> Ciclos -> Cursos
    """
    try:
        # Query base para carreras activas
        query = db.query(Carrera).filter(Carrera.is_active == True)
        
        carreras = query.options(
            joinedload(Carrera.ciclos).joinedload(Ciclo.cursos),
            joinedload(Carrera.estudiantes)
        ).all()
        
        estructura = []
        for carrera in carreras:
            ciclos_data = []
            for ciclo in carrera.ciclos:
                if año and ciclo.año != año:
                    continue
                    
                # Obtener estudiantes matriculados en este ciclo
                matriculas = db.query(Matricula).filter(
                    Matricula.ciclo_id == ciclo.id,
                    Matricula.estado == "activa"
                ).options(joinedload(Matricula.estudiante)).all()
                
                estudiantes_matriculados = [m.estudiante for m in matriculas]
                total_estudiantes_matriculados = len(estudiantes_matriculados)
                
                # Obtener cursos activos del ciclo
                cursos_activos = db.query(Curso).filter(
                    Curso.ciclo_id == ciclo.id,
                    Curso.is_active == True
                ).all()
                
                # Verificar si hay cursos pendientes (estudiantes sin notas completas)
                cursos_pendientes = False
                for curso in cursos_activos:
                    notas_curso_count = db.query(Nota).filter(Nota.curso_id == curso.id).count()
                    if notas_curso_count < total_estudiantes_matriculados:
                        cursos_pendientes = True
                        break
                
                # Calcular estadísticas por estudiante único del ciclo
                estudiantes_promedios_ciclo = {}
                
                # Para cada estudiante matriculado, calcular su promedio del ciclo
                for estudiante in estudiantes_matriculados:
                    # Obtener todas las notas del estudiante en cursos activos del ciclo
                    notas_estudiante = db.query(Nota).join(Curso).filter(
                        Nota.estudiante_id == estudiante.id,
                        Curso.ciclo_id == ciclo.id,
                        Curso.is_active == True
                    ).all()
                    
                    # Calcular promedio de cada curso para este estudiante
                    promedios_cursos_estudiante = []
                    for nota in notas_estudiante:
                        promedio_curso = GradeCalculator.calcular_promedio_nota(nota)
                        if promedio_curso is not None:
                            promedios_cursos_estudiante.append(float(promedio_curso))
                    
                    # Si el estudiante tiene al menos un promedio de curso, calcular promedio del ciclo
                    if promedios_cursos_estudiante:
                        # Promedio del ciclo = promedio simple de los promedios de cursos
                        promedio_ciclo_estudiante = sum(promedios_cursos_estudiante) / len(promedios_cursos_estudiante)
                        estudiantes_promedios_ciclo[estudiante.id] = promedio_ciclo_estudiante
                
                # Calcular estadísticas del ciclo basadas en estudiantes únicos
                aprobados_ciclo = 0
                desaprobados_ciclo = 0
                suma_promedios_ciclo = 0
                
                # Contar aprobados/desaprobados basado en estudiantes únicos matriculados
                for estudiante in estudiantes_matriculados:
                    if estudiante.id in estudiantes_promedios_ciclo:
                        # Estudiante con promedio calculado
                        promedio_estudiante = estudiantes_promedios_ciclo[estudiante.id]
                        suma_promedios_ciclo += promedio_estudiante
                        
                        if promedio_estudiante >= float(GradeCalculator.NOTA_MINIMA_APROBACION):
                            aprobados_ciclo += 1
                        else:
                            desaprobados_ciclo += 1
                    else:
                        # Estudiante sin notas registradas - se considera desaprobado
                        desaprobados_ciclo += 1
                
                # Promedio general del ciclo
                promedio_ciclo = round(suma_promedios_ciclo / len(estudiantes_promedios_ciclo), 2) if estudiantes_promedios_ciclo else 0
                
                cursos_data = []
                for curso in ciclo.cursos:
                    if not curso.is_active:
                        continue
                        
                    # Obtener todas las notas del curso
                    notas_curso = db.query(Nota).filter(Nota.curso_id == curso.id).all()
                    
                    # Contar estudiantes únicos en el curso
                    estudiantes_curso = set()
                    aprobados = 0
                    desaprobados = 0
                    suma_promedios = 0
                    total_con_promedio = 0
                    
                    for nota in notas_curso:
                        estudiantes_curso.add(nota.estudiante_id)
                        promedio_estudiante = GradeCalculator.calcular_promedio_nota(nota)
                        if promedio_estudiante is not None:
                            suma_promedios += float(promedio_estudiante)
                            total_con_promedio += 1
                            if promedio_estudiante >= GradeCalculator.NOTA_MINIMA_APROBACION:
                                aprobados += 1
                            else:
                                desaprobados += 1
                    
                    # Promedio del curso basado en cálculos correctos
                    promedio_curso = round(suma_promedios / total_con_promedio, 2) if total_con_promedio > 0 else 0
                    
                    cursos_data.append({
                        "id": curso.id,
                        "nombre": curso.nombre,
                        "descripcion": curso.descripcion,
                        "docente": curso.docente.full_name if curso.docente else "Sin asignar",
                        "estudiantes_count": len(estudiantes_curso),  # Usar estudiantes únicos
                        "aprobados": aprobados,
                        "desaprobados": desaprobados,
                        "promedio": promedio_curso
                    })
                
                ciclos_data.append({
                    "id": ciclo.id,
                    "nombre": ciclo.nombre,
                    "numero": ciclo.numero,
                    "año": ciclo.año,
                    "fecha_inicio": ciclo.fecha_inicio.isoformat(),
                    "fecha_fin": ciclo.fecha_fin.isoformat(),
                    "estudiantes_count": total_estudiantes_matriculados,  # Usar total de estudiantes matriculados
                    "aprobados": aprobados_ciclo,
                    "desaprobados": desaprobados_ciclo,
                    "promedio": promedio_ciclo,
                    "cursos_pendientes": cursos_pendientes,
                    "cursos": cursos_data
                })
            
            if ciclos_data or not año:  # Incluir carrera si tiene ciclos o no hay filtro de año
                estructura.append({
                    "id": carrera.id,
                    "nombre": carrera.nombre,
                    "codigo": carrera.codigo,
                    "descripcion": carrera.descripcion,
                    "duracion_ciclos": carrera.duracion_ciclos,
                    "estudiantes_count": len(carrera.estudiantes),
                    "ciclos": ciclos_data
                })
        
        return {
            "success": True,
            "data": estructura,
            "total_carreras": len(estructura),
            "año_filtro": año
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estructura jerárquica: {str(e)}"
        )

@router.get("/promedios/por-ciclo")
async def get_promedios_por_ciclo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    año: Optional[int] = Query(None, description="Filtrar por año específico"),
    carrera_id: Optional[int] = Query(None, description="Filtrar por carrera específica")
):
    """
    Obtiene promedios agregados por ciclo académico
    """
    try:
        # Query base para ciclos
        query = db.query(Ciclo).filter(Ciclo.is_active == True)
        
        if año:
            query = query.filter(Ciclo.año == año)
        if carrera_id:
            query = query.filter(Ciclo.carrera_id == carrera_id)
        
        ciclos = query.options(joinedload(Ciclo.carrera)).all()
        
        promedios_data = []
        for ciclo in ciclos:
            # Calcular estadísticas del ciclo
            notas_query = db.query(Nota).join(Curso).filter(Curso.ciclo_id == ciclo.id)
            
            # Contar estudiantes únicos
            estudiantes_count = notas_query.join(User).filter(User.role == RoleEnum.ESTUDIANTE).distinct(User.id).count()
            
            # Calcular promedio general del ciclo
            promedios_individuales = []
            for nota in notas_query.all():
                promedio_individual = GradeCalculator.calcular_promedio_nota(nota)
                if promedio_individual and float(promedio_individual) > 0:
                    promedios_individuales.append(float(promedio_individual))
            
            promedio_ciclo = sum(promedios_individuales) / len(promedios_individuales) if promedios_individuales else 0
            aprobados = len([p for p in promedios_individuales if p >= 13])
            porcentaje_aprobacion = (aprobados / len(promedios_individuales) * 100) if promedios_individuales else 0
            
            promedios_data.append({
                "ciclo_id": ciclo.id,
                "ciclo_nombre": ciclo.nombre,
                "ciclo_numero": ciclo.numero,
                "año": ciclo.año,
                "carrera": ciclo.carrera.nombre,
                "carrera_codigo": ciclo.carrera.codigo,
                "estudiantes_count": estudiantes_count,
                "promedio_general": round(promedio_ciclo, 2),
                "aprobados": aprobados,
                "desaprobados": len(promedios_individuales) - aprobados,
                "porcentaje_aprobacion": round(porcentaje_aprobacion, 2),
                "fecha_inicio": ciclo.fecha_inicio.isoformat(),
                "fecha_fin": ciclo.fecha_fin.isoformat()
            })
        
        return {
            "success": True,
            "data": promedios_data,
            "total_ciclos": len(promedios_data),
            "filtros": {
                "año": año,
                "carrera_id": carrera_id
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener promedios por ciclo: {str(e)}"
        )

@router.get("/filtros/años-disponibles")
async def get_años_disponibles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Obtiene los años disponibles en el sistema para filtros
    """
    try:
        años = db.query(Ciclo.año).distinct().filter(Ciclo.is_active == True).order_by(Ciclo.año.desc()).all()
        años_list = [año[0] for año in años]
        
        return {
            "success": True,
            "data": años_list,
            "total": len(años_list)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener años disponibles: {str(e)}"
        )

@router.get("/curso/{curso_id}/estudiantes")
async def get_estudiantes_por_curso(
    curso_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    estado: Optional[str] = Query(None, description="Filtrar por estado: aprobado, desaprobado, todos")
):
    """
    Obtiene los estudiantes de un curso específico con su estado de aprobación
    """
    try:
        # Verificar que el curso existe
        curso = db.query(Curso).filter(Curso.id == curso_id, Curso.is_active == True).first()
        if not curso:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Curso no encontrado"
            )
        
        # Obtener todas las notas del curso con información del estudiante
        notas = db.query(Nota).options(
            joinedload(Nota.estudiante)
        ).filter(Nota.curso_id == curso_id).all()
        
        estudiantes_data = []
        aprobados = []
        desaprobados = []
        
        for nota in notas:
            estudiante = nota.estudiante
            promedio_final = GradeCalculator.calcular_promedio_nota(nota)
            
            if promedio_final is not None:
                es_aprobado = promedio_final >= GradeCalculator.NOTA_MINIMA_APROBACION
                estado_estudiante = "aprobado" if es_aprobado else "desaprobado"
                
                estudiante_info = {
                    "id": estudiante.id,
                    "dni": estudiante.dni,
                    "nombre_completo": estudiante.full_name,
                    "email": estudiante.email,
                    "promedio_final": float(promedio_final),
                    "estado": estado_estudiante,
                    "notas_detalle": {
                        "evaluaciones": [
                            float(nota.evaluacion1 or 0), float(nota.evaluacion2 or 0),
                            float(nota.evaluacion3 or 0), float(nota.evaluacion4 or 0),
                            float(nota.evaluacion5 or 0), float(nota.evaluacion6 or 0),
                            float(nota.evaluacion7 or 0), float(nota.evaluacion8 or 0)
                        ],
                        "practicas": [
                            float(nota.practica1 or 0), float(nota.practica2 or 0),
                            float(nota.practica3 or 0), float(nota.practica4 or 0)
                        ],
                        "parciales": [
                            float(nota.parcial1 or 0), float(nota.parcial2 or 0)
                        ]
                    }
                }
                
                if es_aprobado:
                    aprobados.append(estudiante_info)
                else:
                    desaprobados.append(estudiante_info)
                
                estudiantes_data.append(estudiante_info)
        
        # Filtrar según el parámetro estado
        if estado == "aprobado":
            estudiantes_filtrados = aprobados
        elif estado == "desaprobado":
            estudiantes_filtrados = desaprobados
        else:
            estudiantes_filtrados = estudiantes_data
        
        return {
            "success": True,
            "data": {
                "curso": {
                    "id": curso.id,
                    "nombre": curso.nombre,
                    "descripcion": curso.descripcion,
                    "docente": curso.docente.full_name if curso.docente else "Sin asignar"
                },
                "estudiantes": estudiantes_filtrados,
                "estadisticas": {
                    "total": len(estudiantes_data),
                    "aprobados": len(aprobados),
                    "desaprobados": len(desaprobados),
                    "porcentaje_aprobacion": round((len(aprobados) / len(estudiantes_data)) * 100, 2) if estudiantes_data else 0
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estudiantes del curso: {str(e)}"
        )

@router.get("/estudiantes-por-ciclo/{ciclo_id}")
async def get_estudiantes_por_ciclo(
    ciclo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    estado: Optional[str] = Query(None, description="Filtrar por estado: aprobado, desaprobado, todos")
):
    """
    Obtiene los estudiantes de un ciclo específico con su promedio ponderado de todos los cursos del ciclo
    """
    try:
        # Verificar que el ciclo existe
        ciclo = db.query(Ciclo).filter(Ciclo.id == ciclo_id, Ciclo.is_active == True).first()
        if not ciclo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ciclo no encontrado"
            )
        
        # Obtener todos los cursos del ciclo
        cursos = db.query(Curso).filter(Curso.ciclo_id == ciclo_id, Curso.is_active == True).all()
        
        if not cursos:
            return {
                "success": True,
                "data": {
                    "ciclo": {
                        "id": ciclo.id,
                        "nombre": ciclo.nombre,
                        "numero": ciclo.numero,
                        "año": ciclo.año
                    },
                    "estudiantes": [],
                    "estadisticas": {
                        "total": 0,
                        "aprobados": 0,
                        "desaprobados": 0,
                        "porcentaje_aprobacion": 0
                    }
                }
            }
        
        # Obtener estudiantes matriculados en el ciclo
        matriculas = db.query(Matricula).filter(
            Matricula.ciclo_id == ciclo_id,
            Matricula.estado == "activa"
        ).options(joinedload(Matricula.estudiante)).all()
        
        estudiantes_data = []
        aprobados = []
        desaprobados = []
        
        for matricula in matriculas:
            estudiante = matricula.estudiante
            
            # Obtener todas las notas del estudiante en los cursos de este ciclo
            notas_ciclo = db.query(Nota).filter(
                Nota.estudiante_id == estudiante.id,
                Nota.curso_id.in_([curso.id for curso in cursos])
            ).options(joinedload(Nota.curso)).all()
            
            if not notas_ciclo:
                continue
            
            # Calcular promedio ponderado de todos los cursos del ciclo
            suma_promedios = 0
            total_cursos = 0
            cursos_detalle = []
            
            for nota in notas_ciclo:
                promedio_curso = GradeCalculator.calcular_promedio_nota(nota)
                if promedio_curso is not None:
                    suma_promedios += promedio_curso
                    total_cursos += 1
                    cursos_detalle.append({
                        "nombre": nota.curso.nombre,
                        "promedio": float(promedio_curso),
                        "notas_detalle": {
                            "evaluaciones": [
                                float(nota.evaluacion1 or 0), float(nota.evaluacion2 or 0),
                                float(nota.evaluacion3 or 0), float(nota.evaluacion4 or 0),
                                float(nota.evaluacion5 or 0), float(nota.evaluacion6 or 0),
                                float(nota.evaluacion7 or 0), float(nota.evaluacion8 or 0)
                            ],
                            "practicas": [
                                float(nota.practica1 or 0), float(nota.practica2 or 0),
                                float(nota.practica3 or 0), float(nota.practica4 or 0)
                            ],
                            "parciales": [
                                float(nota.parcial1 or 0), float(nota.parcial2 or 0)
                            ]
                        }
                    })
            
            if total_cursos > 0:
                # Promedio ponderado del ciclo (promedio de promedios de cursos)
                promedio_ciclo = suma_promedios / total_cursos
                es_aprobado = promedio_ciclo >= GradeCalculator.NOTA_MINIMA_APROBACION
                estado_estudiante = "aprobado" if es_aprobado else "desaprobado"
                
                estudiante_info = {
                    "id": estudiante.id,
                    "dni": estudiante.dni,
                    "nombre_completo": estudiante.full_name,
                    "email": estudiante.email,
                    "promedio_ponderado": float(promedio_ciclo),
                    "estado": estado_estudiante,
                    "total_cursos": total_cursos,
                    "cursos_detalle": cursos_detalle,
                    # Para compatibilidad con el modal existente, agregamos un resumen
                    "notas_detalle": {
                        "evaluaciones": [f"Promedio de {total_cursos} cursos"],
                        "practicas": [f"Promedio de {total_cursos} cursos"],
                        "parciales": [f"Promedio de {total_cursos} cursos"]
                    }
                }
                
                if es_aprobado:
                    aprobados.append(estudiante_info)
                else:
                    desaprobados.append(estudiante_info)
                
                estudiantes_data.append(estudiante_info)
        
        # Filtrar según el parámetro estado
        if estado == "aprobado":
            estudiantes_filtrados = aprobados
        elif estado == "desaprobado":
            estudiantes_filtrados = desaprobados
        else:
            estudiantes_filtrados = estudiantes_data
        
        return {
            "success": True,
            "data": {
                "ciclo": {
                    "id": ciclo.id,
                    "nombre": ciclo.nombre,
                    "numero": ciclo.numero,
                    "año": ciclo.año
                },
                "estudiantes": estudiantes_filtrados,
                "estadisticas": {
                    "total": len(estudiantes_data),
                    "aprobados": len(aprobados),
                    "desaprobados": len(desaprobados),
                    "porcentaje_aprobacion": round((len(aprobados) / len(estudiantes_data)) * 100, 2) if estudiantes_data else 0
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estudiantes del ciclo: {str(e)}"
        )
