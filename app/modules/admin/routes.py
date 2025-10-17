from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import datetime, timedelta

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ...shared.models import User, RoleEnum, Carrera, Ciclo, Curso, Matricula, Nota
from .schemas import AdminDashboard, EstadisticasGenerales, ReporteUsuarios

# Importar las rutas específicas
from .docentes_routes import router as docentes_router
from .estudiantes_routes import router as estudiantes_router
from .cursos_ciclos_routes import router as cursos_ciclos_router
from .matriculas_routes import router as matriculas_router
from .notas_routes import router as notas_router
from .reportes_routes import router as reportes_router
from .performance_routes import router as performance_router

router = APIRouter(prefix="/admin", tags=["Admin"])

# Incluir todas las rutas específicas
router.include_router(docentes_router)
router.include_router(estudiantes_router)
router.include_router(cursos_ciclos_router)
router.include_router(matriculas_router)
router.include_router(notas_router)
router.include_router(reportes_router)
router.include_router(performance_router)

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
    
    # Calcular promedio general real
    promedio_general = db.query(func.avg(Nota.nota_final)).scalar() or 0
    
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
