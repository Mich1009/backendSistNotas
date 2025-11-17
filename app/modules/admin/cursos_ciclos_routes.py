from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ...shared.models import User, RoleEnum, Carrera, Ciclo, Curso, Matricula
from .schemas import (
    CicloCreate, CicloUpdate, CicloResponse,
    CursoCreate, CursoUpdate, CursoResponse, CursoListResponse
)

router = APIRouter(prefix="/cursos-ciclos", tags=["Admin - Cursos y Ciclos"])

# ==================== CICLOS ====================

# Obtiene ciclos
@router.get("/ciclos", response_model=List[CicloResponse])
def get_ciclos(
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Obtener lista de ciclos"""
    
    # Obtener la carrera "Desarrollo de Software" (asumiendo que es la única)
    carrera = db.query(Carrera).filter(
        Carrera.nombre == "Desarrollo de Software",
        Carrera.is_active == True
    ).first()
    
    if not carrera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrera 'Desarrollo de Software' no encontrada"
        )
    
    query = db.query(Ciclo).filter(Ciclo.carrera_id == carrera.id)
    
    if is_active is not None:
        query = query.filter(Ciclo.is_active == is_active)
    
    # Ordenar por año (descendente) y luego por número (ascendente)
    query = query.order_by(Ciclo.año.desc(), Ciclo.numero.asc())
    
    ciclos = query.all()
    
    # Agregar estadísticas
    for ciclo in ciclos:
        ciclo.total_cursos = db.query(Curso).filter(
            Curso.ciclo_id == ciclo.id,
            Curso.is_active == True
        ).count()
        
        # Corregir la consulta de matrículas - ahora están directamente relacionadas con ciclos
        ciclo.total_matriculas = db.query(Matricula).filter(
            Matricula.ciclo_id == ciclo.id,
            Matricula.estado == "activa"
        ).count()
    
    return ciclos

# Crea ciclo
@router.post("/ciclos", response_model=CicloResponse)
def create_ciclo(
    ciclo_data: CicloCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Crear un nuevo ciclo"""
    
    # Obtener la carrera "Desarrollo de Software" automáticamente
    carrera = db.query(Carrera).filter(
        Carrera.nombre == "Desarrollo de Software",
        Carrera.is_active == True
    ).first()
    
    if not carrera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrera 'Desarrollo de Software' no encontrada"
        )
    
    # Crear el ciclo con la carrera automáticamente asignada
    ciclo_dict = ciclo_data.dict()
    ciclo_dict['carrera_id'] = carrera.id
    
    # Calcular automáticamente el año basado en la fecha de inicio
    ciclo_dict['año'] = ciclo_data.fecha_inicio.year
    
    new_ciclo = Ciclo(**ciclo_dict)
    db.add(new_ciclo)
    db.commit()
    db.refresh(new_ciclo)
    
    return new_ciclo

# Actualiza ciclo
@router.put("/ciclos/{ciclo_id}", response_model=CicloResponse)
def update_ciclo(
    ciclo_id: int,
    ciclo_data: CicloUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Actualizar un ciclo existente"""
    
    ciclo = db.query(Ciclo).filter(Ciclo.id == ciclo_id).first()
    
    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado"
        )
    
    # Actualizar campos (excluyendo carrera_id ya que es fijo)
    update_data = ciclo_data.dict(exclude_unset=True)
    # Remover carrera_id si está presente, ya que no debe cambiar
    update_data.pop('carrera_id', None)
    
    for field, value in update_data.items():
        setattr(ciclo, field, value)
    
    db.commit()
    db.refresh(ciclo)
    
    return ciclo

# Elimina ciclo
@router.delete("/ciclos/{ciclo_id}")
def delete_ciclo(
    ciclo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Eliminar definitivamente un ciclo"""
    
    ciclo = db.query(Ciclo).filter(Ciclo.id == ciclo_id).first()
    
    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado"
        )
    
    # Verificar si el ciclo tiene cursos asociados
    cursos_asociados = db.query(Curso).filter(Curso.ciclo_id == ciclo_id).count()
    
    if cursos_asociados > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar el ciclo porque tiene {cursos_asociados} curso(s) asociado(s). Elimine primero los cursos."
        )
    
    # Verificar si hay matrículas asociadas al ciclo
    matriculas_asociadas = db.query(Matricula).filter(Matricula.ciclo_id == ciclo_id).count()
    
    if matriculas_asociadas > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar el ciclo porque tiene {matriculas_asociadas} matrícula(s) asociada(s). Elimine primero las matrículas."
        )
    
    # Eliminar definitivamente el ciclo
    db.delete(ciclo)
    db.commit()
    
    return {"message": "Ciclo eliminado definitivamente"}

# ==================== CURSOS ====================

# Obtiene cursos
@router.get("/cursos", response_model=CursoListResponse)
def get_cursos(
    ciclo_id: Optional[int] = Query(None),
    docente_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(1000, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Obtener lista de cursos con paginación y filtros"""
    
    # Query base con joins para obtener información relacionada
    query = db.query(Curso).options(
        joinedload(Curso.ciclo).joinedload(Ciclo.carrera),
        joinedload(Curso.docente)
    )
    
    # Filtrar solo por la carrera "Desarrollo de Software"
    carrera = db.query(Carrera).filter(
        Carrera.nombre == "Desarrollo de Software",
        Carrera.is_active == True
    ).first()
    
    if carrera:
        query = query.join(Ciclo).filter(Ciclo.carrera_id == carrera.id)
    
    # Aplicar filtros
    if ciclo_id:
        query = query.filter(Curso.ciclo_id == ciclo_id)
    
    if docente_id:
        query = query.filter(Curso.docente_id == docente_id)
    
    if is_active is not None:
        query = query.filter(Curso.is_active == is_active)
    
    if search:
        search_filter = Curso.nombre.ilike(f"%{search}%")
        query = query.filter(search_filter)
    
    # Contar total de registros
    total = query.count()
    
    # Aplicar paginación
    offset = (page - 1) * per_page
    cursos = query.offset(offset).limit(per_page).all()
    
    # Agregar información adicional
    for curso in cursos:
        if curso.ciclo and curso.ciclo.carrera:
            curso.carrera_nombre = curso.ciclo.carrera.nombre
        if curso.ciclo:
            curso.ciclo_nombre = curso.ciclo.nombre
        
        # Agregar nombre del docente si está asignado
        if curso.docente:
            curso.docente_nombre = f"{curso.docente.first_name} {curso.docente.last_name}"
        
        # Contar matriculados por ciclo (ya que las matrículas están relacionadas con ciclos, no cursos)
        curso.total_matriculados = db.query(Matricula).filter(
            Matricula.ciclo_id == curso.ciclo_id,
            Matricula.estado == "activa"
        ).count()
    
    return {
        "items": cursos,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }

# Crea curso
@router.post("/cursos", response_model=CursoResponse)
def create_curso(
    curso_data: CursoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Crear un nuevo curso"""
    
    # Verificar que el ciclo existe
    ciclo = db.query(Ciclo).filter(
        Ciclo.id == curso_data.ciclo_id,
        Ciclo.is_active == True
    ).first()
    
    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado o inactivo"
        )
    
    # Crear el curso
    new_curso = Curso(**curso_data.dict())
    db.add(new_curso)
    db.commit()
    db.refresh(new_curso)
    
    return new_curso

# Actualiza curso
@router.put("/cursos/{curso_id}", response_model=CursoResponse)
def update_curso(
    curso_id: int,
    curso_data: CursoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Actualizar un curso existente"""
    
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado"
        )
    
    # Verificar ciclo si se está cambiando
    if curso_data.ciclo_id and curso_data.ciclo_id != curso.ciclo_id:
        ciclo = db.query(Ciclo).filter(
            Ciclo.id == curso_data.ciclo_id,
            Ciclo.is_active == True
        ).first()
        
        if not ciclo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ciclo no encontrado o inactivo"
            )
    
    # Actualizar campos
    for field, value in curso_data.dict(exclude_unset=True).items():
        setattr(curso, field, value)
    
    db.commit()
    db.refresh(curso)
    
    return curso

# Elimina curso
@router.delete("/cursos/{curso_id}")
def delete_curso(
    curso_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Eliminar definitivamente un curso"""
    
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado"
        )
    
    # Since matriculas are no longer related to courses, we can delete courses directly
    # No need to check for associated matriculas
    
    # Eliminar definitivamente el curso
    db.delete(curso)
    db.commit()
    
    return {"message": "Curso eliminado definitivamente"}