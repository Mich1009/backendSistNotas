from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta

from ...database import get_db
from ..auth.dependencies import get_docente_user
from ..auth.models import User
from .models import Curso, Matricula, Nota, HistorialNota
from .schemas import DocenteDashboard

# Importar routers de otros módulos
from .cursos_routes import router as cursos_router
from .calificaciones_routes import router as calificaciones_router
from .perfil_routes import router as perfil_router
from .reporte_routes import router as reporte_router

router = APIRouter(prefix="/teacher", tags=["Docente"])


# Incluir routers de otros módulos
router.include_router(cursos_router, tags=["Cursos"])
router.include_router(calificaciones_router, tags=["Calificaciones"])
router.include_router(perfil_router, tags=["Perfil"])
router.include_router(reporte_router, tags=["Reportes"])

@router.get("/dashboard", response_model=DocenteDashboard)
def get_teacher_dashboard(
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener dashboard completo del docente con estadísticas avanzadas"""
    
    # Obtener cursos del docente
    cursos = db.query(Curso).filter(
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).options(
        joinedload(Curso.ciclo)
    ).all()
    
    # Convertir cursos a formato de respuesta
    cursos_response = []
    total_estudiantes = 0
    total_notas_pendientes = 0
    promedio_general_acumulado = 0
    estudiantes_aprobados_total = 0
    estudiantes_desaprobados_total = 0
    
    for curso in cursos:
        # Contar estudiantes matriculados en el ciclo del curso
        matriculas = db.query(Matricula).filter(
            Matricula.ciclo_id == curso.ciclo_id,
            Matricula.estado == "activa"
        ).all()
        
        estudiantes_count = len(matriculas)
        total_estudiantes += estudiantes_count
        
        # Calcular estadísticas de notas para este curso
        notas_curso = db.query(Nota).filter(
            Nota.curso_id == curso.id
        ).all()
        
        # Contar notas pendientes (estudiantes sin promedio final)
        estudiantes_con_notas = 0
        for matricula in matriculas:
            nota_estudiante = next((n for n in notas_curso if n.estudiante_id == matricula.estudiante_id), None)
            if nota_estudiante and nota_estudiante.calcular_promedio_final() > 0:
                estudiantes_con_notas += 1
        
        notas_pendientes = estudiantes_count - estudiantes_con_notas
        total_notas_pendientes += notas_pendientes
        
        # Calcular promedio del curso y estudiantes aprobados/desaprobados
        promedio_curso = 0
        aprobados_curso = 0
        desaprobados_curso = 0
        
        if notas_curso:
            # Calcular promedio ponderado por estudiante
            promedios_estudiantes = []
            for matricula in matriculas:
                nota_estudiante = next((n for n in notas_curso if n.estudiante_id == matricula.estudiante_id), None)
                if nota_estudiante and nota_estudiante.calcular_promedio_final() > 0:
                    promedio_final = nota_estudiante.calcular_promedio_final()
                    promedios_estudiantes.append(promedio_final)
                    
                    # Verificar aprobación (nota >= 13.0)
                    if promedio_final >= 13.0:
                        aprobados_curso += 1
                    else:
                        desaprobados_curso += 1
            
            if promedios_estudiantes:
                promedio_curso = sum(promedios_estudiantes) / len(promedios_estudiantes)
                promedio_general_acumulado += promedio_curso
        
        estudiantes_aprobados_total += aprobados_curso
        estudiantes_desaprobados_total += desaprobados_curso
        
        curso_data = {
            "id": curso.id,
            "nombre": curso.nombre,
            "ciclo_id": curso.ciclo_id,
            "docente_id": curso.docente_id,
            "is_active": curso.is_active,
            "created_at": curso.created_at,
            "ciclo_nombre": curso.ciclo.nombre if curso.ciclo else "Sin ciclo",
            "ciclo_año": curso.ciclo.año if curso.ciclo else None,
            "total_estudiantes": estudiantes_count,
            "promedio_curso": round(promedio_curso, 2) if promedio_curso > 0 else None,
            "estudiantes_aprobados": aprobados_curso,
            "estudiantes_desaprobados": desaprobados_curso,
            "notas_pendientes": notas_pendientes
        }
        cursos_response.append(curso_data)
    
    # Estadísticas generales
    total_cursos = len(cursos)
    promedio_general = round(promedio_general_acumulado / total_cursos, 2) if total_cursos > 0 else 0
    
    # Calcular promedio de estudiantes por curso
    promedio_estudiantes = total_estudiantes / total_cursos if total_cursos > 0 else 0
    
    # Obtener ciclos únicos
    ciclos_unicos = list(set([curso.ciclo_id for curso in cursos]))
    total_ciclos = len(ciclos_unicos)
    
    # Actividad reciente - últimas modificaciones de notas
    actividad_reciente = []
    historial_reciente = db.query(HistorialNota).filter(
        HistorialNota.fecha_modificacion >= datetime.now() - timedelta(days=7)
    ).join(Nota).join(Curso).filter(
        Curso.docente_id == current_user.id
    ).order_by(HistorialNota.fecha_modificacion.desc()).limit(5).all()
    
    for historial in historial_reciente:
        actividad_reciente.append({
            "id": historial.id,
            "accion": f"Nota modificada en {historial.nota.curso.nombre}",
            "descripcion": f"Estudiante ID {historial.estudiante_id}: {historial.nota_anterior} → {historial.nota_nueva}",
            "fecha": historial.fecha_modificacion.strftime("%Y-%m-%d %H:%M"),
            "tiempo_relativo": calcular_tiempo_relativo(historial.fecha_modificacion)
        })
    
    # Si no hay historial reciente, agregar actividades simuladas
    if not actividad_reciente:
        actividad_reciente = [
            {
                "id": 1,
                "accion": "Dashboard actualizado",
                "descripcion": "Estadísticas recalculadas automáticamente",
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "tiempo_relativo": "Hace unos momentos"
            }
        ]
    
    return {
        "docente_info": {
            "id": current_user.id,
            "nombre_completo": f"{current_user.first_name} {current_user.last_name}",
            "email": current_user.email,
            "especialidad": current_user.especialidad or "No especificada",
            "grado_academico": current_user.grado_academico or "No especificado"
        },
        "estadisticas_generales": {
            "total_cursos": total_cursos,
            "total_estudiantes": total_estudiantes,
            "total_ciclos": total_ciclos,
            "promedio_estudiantes_por_curso": round(promedio_estudiantes, 2),
            "promedio_general": promedio_general,
            "estudiantes_aprobados": estudiantes_aprobados_total,
            "estudiantes_desaprobados": estudiantes_desaprobados_total,
            "notas_pendientes": total_notas_pendientes,
            "tasa_aprobacion": round((estudiantes_aprobados_total / (estudiantes_aprobados_total + estudiantes_desaprobados_total)) * 100, 2) if (estudiantes_aprobados_total + estudiantes_desaprobados_total) > 0 else 0
        },
        "cursos_actuales": cursos_response,
        "actividad_reciente": actividad_reciente
    }

def calcular_tiempo_relativo(fecha):
    """Calcular tiempo relativo desde una fecha"""
    ahora = datetime.now()
    diferencia = ahora - fecha
    
    if diferencia.days > 0:
        return f"Hace {diferencia.days} día{'s' if diferencia.days > 1 else ''}"
    elif diferencia.seconds > 3600:
        horas = diferencia.seconds // 3600
        return f"Hace {horas} hora{'s' if horas > 1 else ''}"
    elif diferencia.seconds > 60:
        minutos = diferencia.seconds // 60
        return f"Hace {minutos} minuto{'s' if minutos > 1 else ''}"
    else:
        return "Hace unos momentos"