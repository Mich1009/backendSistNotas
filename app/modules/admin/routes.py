from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ...shared.models import User, RoleEnum, Carrera, Ciclo, Curso, Matricula, Nota
from .schemas import AdminDashboard, EstadisticasGenerales, ReporteUsuarios
from ...shared.grade_utils import calcular_promedio_nota, contar_notas_por_rango

# Importar las rutas específicas
from .docentes_routes import router as docentes_router
from .estudiantes_routes import router as estudiantes_router
from .cursos_ciclos_routes import router as cursos_ciclos_router
from .matriculas_routes import router as matriculas_router
from .reportes_routes import router as reportes_router

router = APIRouter(prefix="/admin", tags=["Admin"])

# Incluir todas las rutas específicas
router.include_router(docentes_router)
router.include_router(estudiantes_router)
router.include_router(cursos_ciclos_router)
router.include_router(matriculas_router)
router.include_router(reportes_router)

@router.get("/dashboard", response_model=AdminDashboard)
def get_admin_dashboard(
    db: Session = Depends(get_db)
):
    """
    Obtener datos del dashboard administrativo
    """
    
    # Estadísticas generales
    total_usuarios = db.query(User).filter(User.is_active == True).count()
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
    total_carreras = db.query(Carrera).filter(Carrera.is_active == True).count()
    total_ciclos = db.query(Ciclo).filter(Ciclo.is_active == True).count()
    total_cursos = db.query(Curso).filter(Curso.is_active == True).count()
    usuarios_activos = db.query(User).filter(User.is_active == True).count()
    usuarios_inactivos = db.query(User).filter(User.is_active == False).count()
    
    # Calcular promedio general real usando los campos existentes
    # Obtener todas las notas y calcular el promedio manualmente
    notas = db.query(Nota).all()
    promedios_calculados = []
    
    for nota in notas:
        # Recolectar todas las evaluaciones válidas
        evaluaciones = []
        for i in range(1, 9):
            eval_val = getattr(nota, f'evaluacion{i}')
            if eval_val is not None and float(eval_val) > 0:
                evaluaciones.append(float(eval_val))
        
        # Recolectar todas las prácticas válidas
        practicas = []
        for i in range(1, 5):
            prac_val = getattr(nota, f'practica{i}')
            if prac_val is not None and float(prac_val) > 0:
                practicas.append(float(prac_val))
        
        # Recolectar todos los parciales válidos
        parciales = []
        for i in range(1, 3):
            parc_val = getattr(nota, f'parcial{i}')
            if parc_val is not None and float(parc_val) > 0:
                parciales.append(float(parc_val))
        
        # Calcular promedio si hay notas
        todas_notas = evaluaciones + practicas + parciales
        if todas_notas:
            promedio_nota = sum(todas_notas) / len(todas_notas)
            promedios_calculados.append(promedio_nota)
    
    promedio_general = sum(promedios_calculados) / len(promedios_calculados) if promedios_calculados else 0
    
    estadisticas = EstadisticasGenerales(
        total_usuarios=total_usuarios,
        total_estudiantes=total_estudiantes,
        total_docentes=total_docentes,
        total_admins=total_admins,
        total_carreras=total_carreras,
        total_ciclos=total_ciclos,
        total_cursos=total_cursos,
        total_matriculas=db.query(Matricula).count(),
        usuarios_activos=usuarios_activos,
        usuarios_inactivos=usuarios_inactivos,
        promedio_general=round(promedio_general, 2)
    )
    
    # Actividad reciente (últimos 7 días)
    fecha_limite = datetime.utcnow() - timedelta(days=7)
    usuarios_recientes = db.query(User).filter(
        User.created_at >= fecha_limite
    ).order_by(User.created_at.desc()).limit(10).all()
    
    actividad_reciente = [
        {
            "tipo": "nuevo_usuario",
            "descripcion": f"Nuevo {usuario.role.value}: {usuario.first_name} {usuario.last_name}",
            "fecha": usuario.created_at,
            "usuario_id": usuario.id
        }
        for usuario in usuarios_recientes
    ]
    
    # Alertas del sistema
    alertas = []
    
    # Verificar usuarios sin actividad reciente
    usuarios_inactivos = db.query(User).filter(
        User.is_active == True,
        User.created_at < fecha_limite
    ).count()
    
    if usuarios_inactivos > 0:
        alertas.append({
            "tipo": "warning",
            "mensaje": f"{usuarios_inactivos} usuarios sin actividad reciente",
            "fecha": datetime.utcnow()
        })
    
    # Nota: Ya no verificamos cursos sin docente asignado porque el modelo Curso
    # ya no tiene relación directa con docentes
    
    return AdminDashboard(
        estadisticas_generales=estadisticas.model_dump(),
        usuarios_recientes=usuarios_recientes,
        actividad_sistema=actividad_reciente,
        alertas=alertas
    )

@router.get("/grade-distribution")
def get_grade_distribution(
    db: Session = Depends(get_db)
):
    """
    Obtener distribución de calificaciones para el dashboard
    """
    try:
        # Obtener todas las notas y calcular promedios
        todas_notas = db.query(Nota).all()
        promedios_validos = []
        for nota in todas_notas:
            promedio = calcular_promedio_nota(nota)
            if promedio is not None:
                promedios_validos.append(promedio)
        
        # Distribución de notas por rangos
        total_notas = len(promedios_validos)
        
        excelente = contar_notas_por_rango(db, 18)
        bueno = contar_notas_por_rango(db, 14, 18)
        regular = contar_notas_por_rango(db, 11, 14)
        deficiente = contar_notas_por_rango(db, 0, 11)
        
        distribucion_notas = [
            {"categoria": "Excelente (18-20)", "cantidad": excelente},
            {"categoria": "Bueno (14-17)", "cantidad": bueno},
            {"categoria": "Regular (11-13)", "cantidad": regular},
            {"categoria": "Deficiente (0-10)", "cantidad": deficiente}
        ]
        
        return [
            {
                "categoria": item["categoria"],
                "cantidad": item["cantidad"],
                "porcentaje": round((item["cantidad"] / (total_notas or 1)) * 100, 2)
            }
            for item in distribucion_notas
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo distribución de calificaciones: {str(e)}")

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

# ==================== ESTUDIANTES POR CICLO ====================
@router.get("/estudiantes-por-ciclo")
def get_estudiantes_por_ciclo(
    year: Optional[int] = Query(None, description="Año para filtrar (opcional)"),
    db: Session = Depends(get_db)
):
    """Obtener número de estudiantes por ciclo basado en su matrícula del ciclo más alto, opcionalmente filtrado por año del ciclo"""
    
    try:
        # Subquery para obtener el ciclo más alto (mayor número) de cada estudiante
        subquery_ciclo_mas_alto = db.query(
            Matricula.estudiante_id,
            func.max(Ciclo.numero).label('ciclo_numero_maximo')
        ).join(
            Ciclo, Matricula.ciclo_id == Ciclo.id
        ).filter(
            Matricula.estado == "activa",
            Ciclo.is_active == True
        ).group_by(Matricula.estudiante_id).subquery()
        
        # Query principal para obtener estudiantes por ciclo basado en su ciclo más alto
        query = db.query(
            Ciclo.nombre.label('ciclo'),
            Ciclo.año.label('año_ciclo'),
            func.count(func.distinct(Matricula.estudiante_id)).label('numero_estudiantes')
        ).join(
            Matricula, Ciclo.id == Matricula.ciclo_id
        ).join(
            subquery_ciclo_mas_alto,
            (Matricula.estudiante_id == subquery_ciclo_mas_alto.c.estudiante_id) &
            (Ciclo.numero == subquery_ciclo_mas_alto.c.ciclo_numero_maximo)
        ).filter(
            Matricula.estado == "activa",
            Ciclo.is_active == True
        )
        
        # Filtrar por año del ciclo si se proporciona
        if year:
            query = query.filter(Ciclo.año == year)
        
        # Agrupar por ciclo y año, ordenar por número del ciclo
        results = query.group_by(Ciclo.id, Ciclo.nombre, Ciclo.año, Ciclo.numero).order_by(Ciclo.numero).all()
        
        # Convertir a formato esperado por el frontend
        estadisticas = [
            {
                "ciclo": result.ciclo,
                "numero_estudiantes": result.numero_estudiantes,
                "año": result.año_ciclo
            }
            for result in results
        ]
        
        # Obtener años disponibles basados en los años de los ciclos
        años_query = db.query(
            Ciclo.año.label('year')
        ).join(
            Matricula, Ciclo.id == Matricula.ciclo_id
        ).filter(
            Matricula.estado == "activa",
            Ciclo.is_active == True
        ).distinct().order_by(desc('year'))
        
        años_disponibles = [int(year.year) for year in años_query.all() if year.year]
        
        return {
            "estadisticas": estadisticas,
            "años_disponibles": años_disponibles
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas de estudiantes por ciclo: {str(e)}"
        )
