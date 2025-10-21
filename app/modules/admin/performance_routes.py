from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.database import get_db
from app.modules.auth.dependencies import get_admin_user
from app.shared.models import User, Carrera, Ciclo, Curso, Matricula, Nota, HistorialNota, RoleEnum
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any
import os

router = APIRouter(prefix="/performance")

@router.get("/system-health")
async def get_system_health(
    # current_user=Depends(get_admin_user),  # Comentado temporalmente para pruebas
    db: Session = Depends(get_db)
):
    """
    Obtiene métricas de salud del sistema incluyendo CPU, memoria, disco y base de datos
    """
    try:
        # Métricas del sistema
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Métricas de la base de datos
        db_metrics = await get_database_metrics(db)
        
        # Estado general del sistema
        system_status = "healthy"
        if cpu_percent > 80 or memory.percent > 85 or disk.percent > 90:
            system_status = "warning"
        if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
            system_status = "critical"
        
        return {
            "status": system_status,
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu": {
                    "usage_percent": round(cpu_percent, 2),
                    "cores": psutil.cpu_count(),
                    "status": "normal" if cpu_percent < 80 else "high" if cpu_percent < 95 else "critical"
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": round(memory.percent, 2),
                    "status": "normal" if memory.percent < 85 else "high" if memory.percent < 95 else "critical"
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": round((disk.used / disk.total) * 100, 2),
                    "status": "normal" if disk.percent < 90 else "high" if disk.percent < 95 else "critical"
                }
            },
            "database": db_metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo métricas del sistema: {str(e)}")

@router.get("/performance-metrics")
async def get_performance_metrics(
    # current_user=Depends(get_admin_user),  # Comentado temporalmente para pruebas
    db: Session = Depends(get_db)
):
    """
    Obtiene métricas de rendimiento del sistema educativo
    """
    try:
        # Métricas de usuarios activos
        total_estudiantes = db.query(User).filter(User.is_active == True, User.role == RoleEnum.ESTUDIANTE).count()
        total_docentes = db.query(User).filter(User.is_active == True, User.role == RoleEnum.DOCENTE).count()
        total_cursos = db.query(Curso).filter(Curso.is_active == True).count()
        
        # Métricas de actividad reciente (últimos 30 días)
        fecha_limite = datetime.now() - timedelta(days=30)
        
        # Notas registradas recientemente
        notas_recientes = db.query(Nota).filter(
            Nota.created_at >= fecha_limite
        ).count()
        
        # Matrículas recientes
        matriculas_recientes = db.query(Matricula).filter(
            Matricula.fecha_matricula >= fecha_limite
        ).count()
        
        # Promedio general del sistema
        promedio_general = db.query(func.avg(Nota.promedio_final)).scalar() or 0
        
        # Distribución de notas - simplificada para evitar errores de SQLAlchemy
        total_notas = db.query(Nota).count()
        
        excelente = db.query(Nota).filter(Nota.promedio_final >= 18).count()
        bueno = db.query(Nota).filter(Nota.promedio_final >= 14, Nota.promedio_final < 18).count()
        regular = db.query(Nota).filter(Nota.promedio_final >= 11, Nota.promedio_final < 14).count()
        deficiente = db.query(Nota).filter(Nota.promedio_final < 11).count()
        
        distribucion_notas = [
            {"categoria": "Excelente (18-20)", "cantidad": excelente},
            {"categoria": "Bueno (14-17)", "cantidad": bueno},
            {"categoria": "Regular (11-13)", "cantidad": regular},
            {"categoria": "Deficiente (0-10)", "cantidad": deficiente}
        ]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overview": {
                "total_estudiantes": total_estudiantes,
                "total_docentes": total_docentes,
                "total_cursos": total_cursos,
                "promedio_general": round(float(promedio_general), 2)
            },
            "activity": {
                "notas_registradas_30d": notas_recientes,
                "matriculas_recientes_30d": matriculas_recientes
            },
            "grade_distribution": [
                {
                    "categoria": item["categoria"],
                    "cantidad": item["cantidad"],
                    "porcentaje": round((item["cantidad"] / (total_notas or 1)) * 100, 2)
                }
                for item in distribucion_notas
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo métricas de rendimiento: {str(e)}")

@router.get("/activity-timeline")
async def get_activity_timeline(
    days: int = 7,
    # current_user=Depends(get_admin_user),  # Comentado temporalmente para pruebas
    db: Session = Depends(get_db)
):
    """
    Obtiene la línea de tiempo de actividad del sistema
    """
    try:
        fecha_inicio = datetime.now() - timedelta(days=days)
        
        # Actividad diaria de notas
        actividad_notas = db.query(
            func.date(Nota.created_at).label('fecha'),
            func.count(Nota.id).label('cantidad')
        ).filter(
            Nota.created_at >= fecha_inicio
        ).group_by(
            func.date(Nota.created_at)
        ).order_by(
            func.date(Nota.created_at)
        ).all()
        
        # Actividad diaria de matrículas
        actividad_matriculas = db.query(
            func.date(Matricula.fecha_matricula).label('fecha'),
            func.count(Matricula.id).label('cantidad')
        ).filter(
            Matricula.fecha_matricula >= fecha_inicio
        ).group_by(
            func.date(Matricula.fecha_matricula)
        ).order_by(
            func.date(Matricula.fecha_matricula)
        ).all()
        
        # Crear timeline completo
        timeline = []
        for i in range(days):
            fecha = (datetime.now() - timedelta(days=days-1-i)).date()
            
            notas_dia = next((item.cantidad for item in actividad_notas if item.fecha == fecha), 0)
            matriculas_dia = next((item.cantidad for item in actividad_matriculas if item.fecha == fecha), 0)
            
            timeline.append({
                "fecha": fecha.isoformat(),
                "notas": notas_dia,
                "matriculas": matriculas_dia,
                "total_actividad": notas_dia + matriculas_dia
            })
        
        return {
            "timeline": timeline,
            "summary": {
                "total_notas": sum(item["notas"] for item in timeline),
                "total_matriculas": sum(item["matriculas"] for item in timeline),
                "promedio_diario": round(sum(item["total_actividad"] for item in timeline) / days, 2)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo timeline de actividad: {str(e)}")

async def get_database_metrics(db: Session) -> Dict[str, Any]:
    """
    Obtiene métricas específicas de la base de datos
    """
    try:
        # Tamaño de las tablas principales
        table_sizes = {}
        tables = ['users', 'cursos', 'notas', 'matriculas', 'ciclos', 'carreras']
        
        for table in tables:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                table_sizes[table] = result or 0
            except:
                table_sizes[table] = 0
        
        # Conexiones activas (si es PostgreSQL)
        try:
            active_connections = db.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            ).scalar()
        except:
            active_connections = "N/A"
        
        return {
            "table_sizes": table_sizes,
            "active_connections": active_connections,
            "status": "connected"
        }
    except Exception as e:
        return {
            "table_sizes": {},
            "active_connections": "Error",
            "status": "error",
            "error": str(e)
        }