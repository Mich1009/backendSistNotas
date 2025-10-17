from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from typing import List, Optional, Dict
from datetime import datetime

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ...shared.models import User, RoleEnum, Curso, Ciclo, Carrera, Matricula, Nota, HistorialNota
from .schemas import UserResponse

router = APIRouter(prefix="/notas", tags=["Admin - Gestión de Notas"])

# ==================== GESTIÓN DE NOTAS ====================

@router.get("/estudiante/{estudiante_id}/notas")
def get_notas_estudiante(
    estudiante_id: int,
    ciclo_id: Optional[int] = Query(None),
    curso_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Obtener todas las notas de un estudiante"""
    
    # Verificar que el estudiante existe
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    # Query base para notas
    query = db.query(Nota).options(
        joinedload(Nota.curso).joinedload(Curso.ciclo).joinedload(Ciclo.carrera),
        joinedload(Nota.estudiante)
    ).filter(Nota.estudiante_id == estudiante_id)
    
    # Aplicar filtros
    if ciclo_id:
        query = query.join(Curso).filter(Curso.ciclo_id == ciclo_id)
    
    if curso_id:
        query = query.filter(Nota.curso_id == curso_id)
    
    notas = query.order_by(desc(Nota.fecha_registro)).all()
    
    # Calcular promedios
    promedio_general = 0
    promedio_ciclo = 0
    
    if notas:
        promedio_general = sum(nota.nota for nota in notas) / len(notas)
        
        if ciclo_id:
            notas_ciclo = [nota for nota in notas if nota.curso.ciclo_id == ciclo_id]
            if notas_ciclo:
                promedio_ciclo = sum(nota.nota for nota in notas_ciclo) / len(notas_ciclo)
    
    # Formatear respuesta
    notas_formateadas = []
    for nota in notas:
        notas_formateadas.append({
            "id": nota.id,
            "nota": nota.nota,
            "fecha_registro": nota.fecha_registro,
            "curso": {
                "id": nota.curso.id,
                "nombre": nota.curso.nombre,
                "ciclo": {
                    "id": nota.curso.ciclo.id,
                    "nombre": nota.curso.ciclo.nombre,
                    "carrera": {
                        "id": nota.curso.ciclo.carrera.id,
                        "nombre": nota.curso.ciclo.carrera.nombre
                    }
                }
            }
        })
    
    return {
        "estudiante": {
            "id": estudiante.id,
            "nombre_completo": estudiante.full_name,
            "dni": estudiante.dni,
            "email": estudiante.email
        },
        "notas": notas_formateadas,
        "total_notas": len(notas),
        "promedio_general": round(promedio_general, 2),
        "promedio_ciclo": round(promedio_ciclo, 2) if ciclo_id else None
    }

@router.get("/curso/{curso_id}/notas")
def get_notas_curso(
    curso_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Obtener todas las notas de un curso"""
    
    # Verificar que el curso existe
    curso = db.query(Curso).options(
        joinedload(Curso.ciclo).joinedload(Ciclo.carrera)
    ).filter(Curso.id == curso_id).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado"
        )
    
    # Query para notas del curso
    query = db.query(Nota).options(
        joinedload(Nota.estudiante)
    ).filter(Nota.curso_id == curso_id)
    
    # Aplicar paginación
    offset = (page - 1) * per_page
    notas = query.offset(offset).limit(per_page).all()
    
    # Calcular estadísticas
    total_notas = query.count()
    promedio_curso = db.query(func.avg(Nota.nota)).filter(
        Nota.curso_id == curso_id
    ).scalar() or 0
    
    nota_maxima = db.query(func.max(Nota.nota)).filter(
        Nota.curso_id == curso_id
    ).scalar() or 0
    
    nota_minima = db.query(func.min(Nota.nota)).filter(
        Nota.curso_id == curso_id
    ).scalar() or 0
    
    # Contar estudiantes por rango de notas
    aprobados = db.query(Nota).filter(
        Nota.curso_id == curso_id,
        Nota.nota >= 11
    ).count()
    
    desaprobados = db.query(Nota).filter(
        Nota.curso_id == curso_id,
        Nota.nota < 11
    ).count()
    
    # Formatear notas
    notas_formateadas = []
    for nota in notas:
        notas_formateadas.append({
            "id": nota.id,
            "nota": nota.nota,
            "fecha_registro": nota.fecha_registro,
            "estudiante": {
                "id": nota.estudiante.id,
                "nombre_completo": nota.estudiante.full_name,
                "dni": nota.estudiante.dni,
                "email": nota.estudiante.email
            }
        })
    
    return {
        "curso": {
            "id": curso.id,
            "nombre": curso.nombre,
            "ciclo": curso.ciclo.nombre,
            "carrera": curso.ciclo.carrera.nombre
        },
        "notas": notas_formateadas,
        "paginacion": {
            "page": page,
            "per_page": per_page,
            "total": total_notas,
            "pages": (total_notas + per_page - 1) // per_page
        },
        "estadisticas": {
            "total_notas": total_notas,
            "promedio": round(promedio_curso, 2),
            "nota_maxima": nota_maxima,
            "nota_minima": nota_minima,
            "aprobados": aprobados,
            "desaprobados": desaprobados,
            "porcentaje_aprobacion": round((aprobados / total_notas * 100), 2) if total_notas > 0 else 0
        }
    }

@router.post("/registrar-nota")
def registrar_nota(
    estudiante_id: int,
    curso_id: int,
    nota: float,
    db: Session = Depends(get_db)
):
    """Registrar una nueva nota para un estudiante"""
    
    # Validar nota
    if not (0 <= nota <= 20):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nota debe estar entre 0 y 20"
        )
    
    # Verificar que el estudiante existe y está activo
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE,
        User.is_active == True
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado o no está activo"
        )
    
    # Verificar que el curso existe y está activo
    curso = db.query(Curso).filter(
        Curso.id == curso_id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no está activo"
        )
    
    # Verificar que el estudiante está matriculado en el curso
    matricula = db.query(Matricula).filter(
        Matricula.estudiante_id == estudiante_id,
        Matricula.curso_id == curso_id,
        Matricula.estado == "activa"
    ).first()
    
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estudiante no está matriculado en este curso"
        )
    
    # Verificar si ya existe una nota para este estudiante en este curso
    nota_existente = db.query(Nota).filter(
        Nota.estudiante_id == estudiante_id,
        Nota.curso_id == curso_id
    ).first()
    
    if nota_existente:
        # Guardar en historial antes de actualizar
        historial = HistorialNota(
             nota_id=nota_existente.id,
             nota_anterior=nota_existente.nota,
             nota_nueva=nota,
             fecha_cambio=datetime.utcnow(),
             usuario_modificador_id=None  # Sin autenticación, no hay usuario
        )
        db.add(historial)
        
        # Actualizar nota existente
        nota_existente.nota = nota
        nota_existente.fecha_registro = datetime.utcnow()
        
        db.commit()
        db.refresh(nota_existente)
        
        return {
            "message": "Nota actualizada exitosamente",
            "nota": {
                "id": nota_existente.id,
                "nota": nota_existente.nota,
                "fecha_registro": nota_existente.fecha_registro,
                "estudiante": estudiante.full_name,
                "curso": curso.nombre
            }
        }
    else:
        # Crear nueva nota
        nueva_nota = Nota(
            estudiante_id=estudiante_id,
            curso_id=curso_id,
            nota=nota,
            fecha_registro=datetime.utcnow()
        )
        
        db.add(nueva_nota)
        db.commit()
        db.refresh(nueva_nota)
        
        return {
            "message": "Nota registrada exitosamente",
            "nota": {
                "id": nueva_nota.id,
                "nota": nueva_nota.nota,
                "fecha_registro": nueva_nota.fecha_registro,
                "estudiante": estudiante.full_name,
                "curso": curso.nombre
            }
        }

@router.put("/nota/{nota_id}")
def actualizar_nota(
    nota_id: int,
    nueva_nota: float,
    db: Session = Depends(get_db)
):
    """Actualizar una nota existente"""
    
    # Validar nota
    if not (0 <= nueva_nota <= 20):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nota debe estar entre 0 y 20"
        )
    
    # Buscar la nota
    nota = db.query(Nota).options(
        joinedload(Nota.estudiante),
        joinedload(Nota.curso)
    ).filter(Nota.id == nota_id).first()
    
    if not nota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota no encontrada"
        )
    
    # Guardar en historial
    historial = HistorialNota(
         nota_id=nota.id,
         nota_anterior=nota.nota,
         nota_nueva=nueva_nota,
         fecha_cambio=datetime.utcnow(),
         usuario_modificador_id=None  # Sin autenticación, no hay usuario
    )
    db.add(historial)
    
    # Actualizar nota
    nota.nota = nueva_nota
    nota.fecha_registro = datetime.utcnow()
    
    db.commit()
    db.refresh(nota)
    
    return {
        "message": "Nota actualizada exitosamente",
        "nota": {
            "id": nota.id,
            "nota": nota.nota,
            "fecha_registro": nota.fecha_registro,
            "estudiante": nota.estudiante.full_name,
            "curso": nota.curso.nombre
        }
    }

@router.delete("/nota/{nota_id}")
def eliminar_nota(
    nota_id: int,
    db: Session = Depends(get_db)
):
    """Eliminar una nota"""
    
    nota = db.query(Nota).filter(Nota.id == nota_id).first()
    
    if not nota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota no encontrada"
        )
    
    # Eliminar historial relacionado
    db.query(HistorialNota).filter(HistorialNota.nota_id == nota_id).delete()
    
    # Eliminar nota
    db.delete(nota)
    db.commit()
    
    return {"message": "Nota eliminada exitosamente"}

@router.get("/historial/{nota_id}")
def get_historial_nota(
    nota_id: int,
    db: Session = Depends(get_db)
):
    """Obtener historial de cambios de una nota"""
    
    # Verificar que la nota existe
    nota = db.query(Nota).filter(Nota.id == nota_id).first()
    if not nota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota no encontrada"
        )
    
    # Obtener historial
    historial = db.query(HistorialNota).options(
        joinedload(HistorialNota.usuario_modificador)
    ).filter(
        HistorialNota.nota_id == nota_id
    ).order_by(desc(HistorialNota.fecha_cambio)).all()
    
    historial_formateado = []
    for registro in historial:
        historial_formateado.append({
            "id": registro.id,
            "nota_anterior": registro.nota_anterior,
            "nota_nueva": registro.nota_nueva,
            "fecha_cambio": registro.fecha_cambio,
            "modificado_por": registro.usuario_modificador.full_name if registro.usuario_modificador else "Usuario eliminado"
        })
    
    return {
        "nota_id": nota_id,
        "historial": historial_formateado,
        "total_cambios": len(historial_formateado)
    }

# ==================== CÁLCULO DE PROMEDIOS ====================

@router.get("/promedios/estudiante/{estudiante_id}")
def get_promedios_estudiante(
    estudiante_id: int,
    db: Session = Depends(get_db)
):
    """Calcular promedios de un estudiante por ciclo"""
    
    # Verificar estudiante
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    # Obtener promedios por ciclo
    promedios_query = db.query(
        Ciclo.id,
        Ciclo.nombre,
        Carrera.nombre.label('carrera_nombre'),
        func.avg(Nota.nota).label('promedio'),
        func.count(Nota.id).label('total_notas')
    ).select_from(Nota).join(
        Curso, Nota.curso_id == Curso.id
    ).join(
        Ciclo, Curso.ciclo_id == Ciclo.id
    ).join(
        Carrera, Ciclo.carrera_id == Carrera.id
    ).filter(
        Nota.estudiante_id == estudiante_id
    ).group_by(
        Ciclo.id, Ciclo.nombre, Carrera.nombre
    ).all()
    
    promedios_por_ciclo = []
    for promedio in promedios_query:
        promedios_por_ciclo.append({
            "ciclo_id": promedio.id,
            "ciclo_nombre": promedio.nombre,
            "carrera": promedio.carrera_nombre,
            "promedio": round(promedio.promedio, 2),
            "total_notas": promedio.total_notas
        })
    
    # Calcular promedio general
    promedio_general = db.query(func.avg(Nota.nota)).filter(
        Nota.estudiante_id == estudiante_id
    ).scalar() or 0
    
    return {
        "estudiante": {
            "id": estudiante.id,
            "nombre_completo": estudiante.full_name,
            "dni": estudiante.dni
        },
        "promedio_general": round(promedio_general, 2),
        "promedios_por_ciclo": promedios_por_ciclo
    }