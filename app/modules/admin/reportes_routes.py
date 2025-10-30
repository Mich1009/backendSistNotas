from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc, asc
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import pandas as pd
import io
import json

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ...shared.models import User, RoleEnum, Carrera, Ciclo, Curso, Matricula, Nota, HistorialNota
from ...shared.grade_utils import calcular_promedio_nota, obtener_notas_con_promedio
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
                    
                # Contar estudiantes matriculados en este ciclo
                estudiantes_count = db.query(Matricula).filter(
                    Matricula.ciclo_id == ciclo.id,
                    Matricula.estado == "activa"
                ).count()
                
                # Calcular estadísticas del ciclo usando GradeCalculator
                # Obtener todas las notas de todos los cursos del ciclo
                notas_ciclo = db.query(Nota).join(Curso).filter(
                    Curso.ciclo_id == ciclo.id,
                    Curso.is_active == True
                ).all()
                
                aprobados_ciclo = 0
                desaprobados_ciclo = 0
                suma_promedios_ciclo = 0
                total_con_promedio_ciclo = 0
                
                for nota in notas_ciclo:
                    promedio_estudiante = GradeCalculator.calcular_promedio_nota(nota)
                    if promedio_estudiante is not None:
                        suma_promedios_ciclo += float(promedio_estudiante)
                        total_con_promedio_ciclo += 1
                        if promedio_estudiante >= GradeCalculator.NOTA_MINIMA_APROBACION:
                            aprobados_ciclo += 1
                        else:
                            desaprobados_ciclo += 1
                
                # Promedio del ciclo basado en cálculos correctos
                promedio_ciclo = round(suma_promedios_ciclo / total_con_promedio_ciclo, 2) if total_con_promedio_ciclo > 0 else 0
                
                cursos_data = []
                for curso in ciclo.cursos:
                    if not curso.is_active:
                        continue
                        
                    # Obtener todas las notas del curso
                    notas_curso = db.query(Nota).filter(Nota.curso_id == curso.id).all()
                    
                    # Contar aprobados y desaprobados usando GradeCalculator
                    aprobados = 0
                    desaprobados = 0
                    suma_promedios = 0
                    total_con_promedio = 0
                    
                    for nota in notas_curso:
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
                        "estudiantes_count": len(notas_curso),
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
                    "estudiantes_count": estudiantes_count,
                    "aprobados": aprobados_ciclo,
                    "desaprobados": desaprobados_ciclo,
                    "promedio": promedio_ciclo,
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

@router.get("/exportar/notas-todos-ciclos")
async def exportar_notas_todos_ciclos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    formato: str = Query("excel", description="Formato de exportación: excel o csv")
):
    """
    Exporta todas las notas de todos los estudiantes de todos los ciclos
    """
    try:
        # Query completa con todas las relaciones
        query = db.query(Nota).options(
            joinedload(Nota.estudiante),
            joinedload(Nota.curso).joinedload(Curso.ciclo).joinedload(Ciclo.carrera)
        ).join(Curso).join(Ciclo).filter(Ciclo.is_active == True)
        
        notas = query.all()
        
        # Preparar datos para exportación
        datos_exportacion = []
        for nota in notas:
            estudiante = nota.estudiante
            curso = nota.curso
            ciclo = curso.ciclo
            carrera = ciclo.carrera
            
            # Calcular promedio final
            promedio_final = calcular_promedio_nota(nota)
            estado = "APROBADO" if promedio_final >= 13 else "DESAPROBADO" if promedio_final > 0 else "PENDIENTE"
            
            datos_exportacion.append({
                "DNI_Estudiante": estudiante.dni,
                "Nombre_Completo": estudiante.full_name,
                "Carrera": carrera.nombre,
                "Ciclo": ciclo.nombre,
                "Año_Ciclo": ciclo.año,
                "Numero_Ciclo": ciclo.numero,
                "Curso": curso.nombre,
                "Docente": curso.docente.full_name if curso.docente else "Sin asignar",
                "Evaluacion_1": float(nota.evaluacion1 or 0),
                "Evaluacion_2": float(nota.evaluacion2 or 0),
                "Evaluacion_3": float(nota.evaluacion3 or 0),
                "Evaluacion_4": float(nota.evaluacion4 or 0),
                "Practica_1": float(nota.practica1 or 0),
                "Practica_2": float(nota.practica2 or 0),
                "Practica_3": float(nota.practica3 or 0),
                "Practica_4": float(nota.practica4 or 0),
                "Parcial_1": float(nota.parcial1 or 0),
                "Parcial_2": float(nota.parcial2 or 0),
                "Promedio_Final": round(promedio_final, 2),
                "Estado": estado,
                "Fecha_Registro": nota.fecha_registro.isoformat()
            })
        
        # Crear DataFrame
        df = pd.DataFrame(datos_exportacion)
        
        if formato.lower() == "excel":
            # Exportar a Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Notas_Todos_Ciclos', index=False)
            
            output.seek(0)
            
            return Response(
                content=output.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=notas_todos_ciclos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                }
            )
        else:
            # Exportar a CSV
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8')
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=notas_todos_ciclos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al exportar notas: {str(e)}"
        )

@router.get("/exportar/notas-por-ciclo/{ciclo_id}")
async def exportar_notas_por_ciclo(
    ciclo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    formato: str = Query("excel", description="Formato de exportación: excel o csv")
):
    """
    Exporta todas las notas de estudiantes de un ciclo específico
    """
    try:
        # Verificar que el ciclo existe
        ciclo = db.query(Ciclo).filter(Ciclo.id == ciclo_id).first()
        if not ciclo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ciclo no encontrado"
            )
        
        # Query para notas del ciclo específico
        query = db.query(Nota).options(
            joinedload(Nota.estudiante),
            joinedload(Nota.curso).joinedload(Curso.docente)
        ).join(Curso).filter(Curso.ciclo_id == ciclo_id)
        
        notas = query.all()
        
        # Preparar datos para exportación
        datos_exportacion = []
        for nota in notas:
            estudiante = nota.estudiante
            curso = nota.curso
            
            # Calcular promedio final
            promedio_final = calcular_promedio_nota(nota)
            estado = "APROBADO" if promedio_final >= 13 else "DESAPROBADO" if promedio_final > 0 else "PENDIENTE"
            
            datos_exportacion.append({
                "DNI_Estudiante": estudiante.dni,
                "Nombre_Completo": estudiante.full_name,
                "Email": estudiante.email,
                "Telefono": estudiante.phone or "N/A",
                "Curso": curso.nombre,
                "Docente": curso.docente.full_name if curso.docente else "Sin asignar",
                "Evaluacion_1": float(nota.evaluacion1 or 0),
                "Evaluacion_2": float(nota.evaluacion2 or 0),
                "Evaluacion_3": float(nota.evaluacion3 or 0),
                "Evaluacion_4": float(nota.evaluacion4 or 0),
                "Evaluacion_5": float(nota.evaluacion5 or 0),
                "Evaluacion_6": float(nota.evaluacion6 or 0),
                "Evaluacion_7": float(nota.evaluacion7 or 0),
                "Evaluacion_8": float(nota.evaluacion8 or 0),
                "Practica_1": float(nota.practica1 or 0),
                "Practica_2": float(nota.practica2 or 0),
                "Practica_3": float(nota.practica3 or 0),
                "Practica_4": float(nota.practica4 or 0),
                "Parcial_1": float(nota.parcial1 or 0),
                "Parcial_2": float(nota.parcial2 or 0),
                "Promedio_Final": round(promedio_final, 2),
                "Estado": estado,
                "Observaciones": nota.observaciones or "",
                "Fecha_Registro": nota.fecha_registro.isoformat()
            })
        
        # Crear DataFrame
        df = pd.DataFrame(datos_exportacion)
        
        if formato.lower() == "excel":
            # Exportar a Excel con múltiples hojas
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Hoja principal con todas las notas
                df.to_excel(writer, sheet_name=f'Notas_{ciclo.nombre}', index=False)
                
                # Hoja de resumen por curso
                resumen_cursos = df.groupby('Curso').agg({
                    'DNI_Estudiante': 'count',
                    'Promedio_Final': ['mean', 'min', 'max'],
                    'Estado': lambda x: (x == 'APROBADO').sum()
                }).round(2)
                
                resumen_cursos.columns = ['Total_Estudiantes', 'Promedio_Curso', 'Nota_Minima', 'Nota_Maxima', 'Aprobados']
                resumen_cursos['Porcentaje_Aprobacion'] = (resumen_cursos['Aprobados'] / resumen_cursos['Total_Estudiantes'] * 100).round(2)
                
                resumen_cursos.to_excel(writer, sheet_name='Resumen_por_Curso')
            
            output.seek(0)
            
            return Response(
                content=output.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=notas_{ciclo.nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                }
            )
        else:
            # Exportar a CSV
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8')
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=notas_{ciclo.nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al exportar notas del ciclo: {str(e)}"
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
                promedio_individual = calcular_promedio_nota(nota)
                if promedio_individual > 0:
                    promedios_individuales.append(promedio_individual)
            
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
