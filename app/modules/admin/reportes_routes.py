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
from .schemas import (
    ReporteUsuarios, ReporteAcademico, EstadisticasGenerales
)

router = APIRouter(prefix="/reportes", tags=["Admin - Reportes"])

# ==================== ESTADÍSTICAS GENERALES ====================

@router.get("/estadisticas-generales", response_model=EstadisticasGenerales)
def get_estadisticas_generales(
    db: Session = Depends(get_db)
):
    """Obtener estadísticas generales del sistema"""
    
    # Contar usuarios por rol
    total_estudiantes = db.query(User).filter(
        User.role == RoleEnum.ESTUDIANTE,
        User.is_active == True
    ).count()
    
    total_docentes = db.query(User).filter(
        User.role == RoleEnum.DOCENTE,
        User.is_active == True
    ).count()
    
    total_admins = db.query(User).filter(
        User.role == RoleEnum.ADMIN,
        User.is_active == True
    ).count()
    
    # Contar total de usuarios y usuarios activos/inactivos
    total_usuarios = db.query(User).count()
    usuarios_activos = db.query(User).filter(User.is_active == True).count()
    usuarios_inactivos = db.query(User).filter(User.is_active == False).count()
    
    # Contar cursos y ciclos activos
    total_cursos = db.query(Curso).filter(Curso.is_active == True).count()
    total_ciclos = db.query(Ciclo).filter(Ciclo.is_active == True).count()
    total_carreras = db.query(Carrera).filter(Carrera.is_active == True).count()
    
    # Contar matrículas activas
    total_matriculas = db.query(Matricula).filter(
        Matricula.estado == "activa"
    ).count()
    
    return EstadisticasGenerales(
        total_usuarios=total_usuarios,
        total_estudiantes=total_estudiantes,
        total_docentes=total_docentes,
        total_admins=total_admins,
        total_cursos=total_cursos,
        total_ciclos=total_ciclos,
        total_carreras=total_carreras,
        total_matriculas=total_matriculas,
        usuarios_activos=usuarios_activos,
        usuarios_inactivos=usuarios_inactivos
    )

# ==================== REPORTES DE RENDIMIENTO ====================

@router.get("/rendimiento-estudiantes")
def get_rendimiento_estudiantes(
    ciclo_id: Optional[int] = Query(None),
    carrera_id: Optional[int] = Query(None),
    curso_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Obtener datos de rendimiento de estudiantes para gráficas"""
    
    # Query base para notas
    query = db.query(
        User.id.label('estudiante_id'),
        User.first_name,
        User.last_name,
        Curso.nombre.label('curso_nombre'),
        Ciclo.nombre.label('ciclo_nombre'),
        Carrera.nombre.label('carrera_nombre'),
        func.avg(Nota.nota).label('promedio')
    ).join(
        Nota, User.id == Nota.estudiante_id
    ).join(
        Curso, Nota.curso_id == Curso.id
    ).join(
        Ciclo, Curso.ciclo_id == Ciclo.id
    ).join(
        Carrera, Ciclo.carrera_id == Carrera.id
    ).filter(
        User.role == RoleEnum.ESTUDIANTE,
        User.is_active == True
    )
    
    # Aplicar filtros
    if ciclo_id:
        query = query.filter(Ciclo.id == ciclo_id)
    
    if carrera_id:
        query = query.filter(Carrera.id == carrera_id)
    
    if curso_id:
        query = query.filter(Curso.id == curso_id)
    
    # Agrupar por estudiante
    resultados = query.group_by(
        User.id, User.first_name, User.last_name,
        Curso.nombre, Ciclo.nombre, Carrera.nombre
    ).all()
    
    # Procesar datos para gráficas
    datos_grafica = []
    rangos_notas = {"0-10": 0, "11-13": 0, "14-16": 0, "17-20": 0}
    
    for resultado in resultados:
        promedio = round(resultado.promedio, 2)
        
        datos_grafica.append({
            "estudiante_id": resultado.estudiante_id,
            "nombre_completo": f"{resultado.first_name} {resultado.last_name}",
            "curso": resultado.curso_nombre,
            "ciclo": resultado.ciclo_nombre,
            "carrera": resultado.carrera_nombre,
            "promedio": promedio
        })
        
        # Clasificar en rangos
        if promedio <= 10:
            rangos_notas["0-10"] += 1
        elif promedio <= 13:
            rangos_notas["11-13"] += 1
        elif promedio <= 16:
            rangos_notas["14-16"] += 1
        else:
            rangos_notas["17-20"] += 1
    
    return {
        "datos_estudiantes": datos_grafica,
        "distribucion_notas": rangos_notas,
        "total_estudiantes": len(datos_grafica),
        "promedio_general": round(sum(d["promedio"] for d in datos_grafica) / len(datos_grafica), 2) if datos_grafica else 0
    }

@router.get("/rendimiento-por-curso")
def get_rendimiento_por_curso(
    ciclo_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Obtener rendimiento promedio por curso"""
    
    query = db.query(
        Curso.id,
        Curso.nombre,
        Ciclo.nombre.label('ciclo_nombre'),
        func.avg(Nota.nota).label('promedio'),
        func.count(func.distinct(Nota.estudiante_id)).label('total_estudiantes'),
        func.count(Nota.id).label('total_notas')
    ).join(
        Nota, Curso.id == Nota.curso_id
    ).join(
        Ciclo, Curso.ciclo_id == Ciclo.id
    ).filter(
        Curso.is_active == True
    )
    
    if ciclo_id:
        query = query.filter(Ciclo.id == ciclo_id)
    
    resultados = query.group_by(
        Curso.id, Curso.nombre, Ciclo.nombre
    ).order_by(desc(func.avg(Nota.nota))).all()
    
    datos_cursos = []
    for resultado in resultados:
        datos_cursos.append({
            "curso_id": resultado.id,
            "nombre": resultado.nombre,
            "ciclo": resultado.ciclo_nombre,
            "promedio": round(resultado.promedio, 2),
            "total_estudiantes": resultado.total_estudiantes,
            "total_notas": resultado.total_notas
        })
    
    return {
        "cursos": datos_cursos,
        "total_cursos": len(datos_cursos)
    }

# ==================== EXPORTACIÓN A EXCEL ====================

@router.get("/exportar/estudiantes")
def exportar_estudiantes_excel(
    ciclo_id: Optional[int] = Query(None),
    carrera_id: Optional[int] = Query(None),
    incluir_notas: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Exportar datos de estudiantes a Excel"""
    
    # Query base para estudiantes
    query = db.query(User).filter(
        User.role == RoleEnum.ESTUDIANTE,
        User.is_active == True
    )
    
    estudiantes = query.all()
    
    # Preparar datos para Excel
    datos_estudiantes = []
    for estudiante in estudiantes:
        datos_estudiantes.append({
            "ID": estudiante.id,
            "DNI": estudiante.dni,
            "Nombres": estudiante.first_name,
            "Apellidos": estudiante.last_name,
            "Email": estudiante.email,
            "Teléfono": estudiante.phone,
            "Fecha Nacimiento": estudiante.fecha_nacimiento,
            "Dirección": estudiante.direccion,
            "Apoderado": estudiante.nombre_apoderado,
            "Teléfono Apoderado": estudiante.telefono_apoderado,
            "Fecha Registro": estudiante.created_at
        })
    
    # Crear DataFrame
    df_estudiantes = pd.DataFrame(datos_estudiantes)
    
    # Crear archivo Excel en memoria
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_estudiantes.to_excel(writer, sheet_name='Estudiantes', index=False)
        
        # Si se incluyen notas, agregar hoja de notas
        if incluir_notas:
            notas_query = db.query(
                User.dni,
                User.first_name,
                User.last_name,
                Curso.nombre.label('curso'),
                Ciclo.nombre.label('ciclo'),
                Nota.nota,
                Nota.fecha_registro
            ).join(
                Nota, User.id == Nota.estudiante_id
            ).join(
                Curso, Nota.curso_id == Curso.id
            ).join(
                Ciclo, Curso.ciclo_id == Ciclo.id
            ).filter(
                User.role == RoleEnum.ESTUDIANTE
            )
            
            if ciclo_id:
                notas_query = notas_query.filter(Ciclo.id == ciclo_id)
            
            notas_data = []
            for nota in notas_query.all():
                notas_data.append({
                    "DNI": nota.dni,
                    "Nombres": nota.first_name,
                    "Apellidos": nota.last_name,
                    "Curso": nota.curso,
                    "Ciclo": nota.ciclo,
                    "Nota": nota.nota,
                    "Fecha": nota.fecha_registro
                })
            
            df_notas = pd.DataFrame(notas_data)
            df_notas.to_excel(writer, sheet_name='Notas', index=False)
    
    output.seek(0)
    
    # Preparar respuesta
    filename = f"estudiantes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/exportar/docentes")
def exportar_docentes_excel(
    db: Session = Depends(get_db)
):
    """Exportar datos de docentes a Excel"""
    
    docentes = db.query(User).filter(
        User.role == RoleEnum.DOCENTE,
        User.is_active == True
    ).all()
    
    datos_docentes = []
    for docente in docentes:
        # Obtener cursos asignados
        cursos = db.query(Curso).filter(
            Curso.docente_id == docente.id,
            Curso.is_active == True
        ).all()
        
        cursos_nombres = ", ".join([curso.nombre for curso in cursos])
        
        datos_docentes.append({
            "ID": docente.id,
            "DNI": docente.dni,
            "Nombres": docente.first_name,
            "Apellidos": docente.last_name,
            "Email": docente.email,
            "Teléfono": docente.phone,
            "Especialidad": docente.especialidad,
            "Grado Académico": docente.grado_academico,
            "Fecha Ingreso": docente.fecha_ingreso,
            "Cursos Asignados": cursos_nombres,
            "Total Cursos": len(cursos),
            "Fecha Registro": docente.created_at
        })
    
    df_docentes = pd.DataFrame(datos_docentes)
    
    # Crear archivo Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_docentes.to_excel(writer, sheet_name='Docentes', index=False)
    
    output.seek(0)
    
    filename = f"docentes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/exportar/notas")
def exportar_notas_excel(
    ciclo_id: Optional[int] = Query(None),
    curso_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Exportar notas a Excel"""
    
    query = db.query(
        User.dni,
        User.first_name,
        User.last_name,
        Curso.nombre.label('curso'),
        Ciclo.nombre.label('ciclo'),
        Carrera.nombre.label('carrera'),
        Nota.nota,
        Nota.fecha_registro,
        User.first_name.label('docente_nombre'),
        User.last_name.label('docente_apellido')
    ).select_from(Nota).join(
        User, Nota.estudiante_id == User.id
    ).join(
        Curso, Nota.curso_id == Curso.id
    ).join(
        Ciclo, Curso.ciclo_id == Ciclo.id
    ).join(
        Carrera, Ciclo.carrera_id == Carrera.id
    ).outerjoin(
        User.alias('docente'), Curso.docente_id == User.id
    )
    
    if ciclo_id:
        query = query.filter(Ciclo.id == ciclo_id)
    
    if curso_id:
        query = query.filter(Curso.id == curso_id)
    
    notas = query.all()
    
    datos_notas = []
    for nota in notas:
        datos_notas.append({
            "DNI Estudiante": nota.dni,
            "Nombres": nota.first_name,
            "Apellidos": nota.last_name,
            "Carrera": nota.carrera,
            "Ciclo": nota.ciclo,
            "Curso": nota.curso,
            "Nota": nota.nota,
            "Fecha Registro": nota.fecha_registro
        })
    
    df_notas = pd.DataFrame(datos_notas)
    
    # Crear archivo Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_notas.to_excel(writer, sheet_name='Notas', index=False)
        
        # Agregar hoja de estadísticas
        if not df_notas.empty:
            estadisticas = {
                "Métrica": [
                    "Total de Notas",
                    "Promedio General",
                    "Nota Máxima",
                    "Nota Mínima",
                    "Estudiantes con Promedio >= 16",
                    "Estudiantes con Promedio < 11"
                ],
                "Valor": [
                    len(df_notas),
                    round(df_notas['Nota'].mean(), 2),
                    df_notas['Nota'].max(),
                    df_notas['Nota'].min(),
                    len(df_notas[df_notas['Nota'] >= 16]),
                    len(df_notas[df_notas['Nota'] < 11])
                ]
            }
            
            df_estadisticas = pd.DataFrame(estadisticas)
            df_estadisticas.to_excel(writer, sheet_name='Estadísticas', index=False)
    
    output.seek(0)
    
    filename = f"notas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )