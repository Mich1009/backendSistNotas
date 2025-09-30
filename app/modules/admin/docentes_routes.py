from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ..auth.security import get_password_hash
from ...shared.models import User, RoleEnum, Curso
from .schemas import UserCreate, UserUpdate, UserResponse, UserListResponse, CursoResponse, CursoAssignment

router = APIRouter(prefix="/docentes", tags=["Admin - Docentes"])

# ==================== CRUD DOCENTES ====================

@router.get("/", response_model=List[UserResponse])
async def get_docentes(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(10, ge=1, le=100, description="Número de registros a obtener"),
    search: Optional[str] = Query(None, description="Buscar por nombre, apellido o email"),
    especialidad: Optional[str] = Query(None, description="Filtrar por especialidad"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    db: Session = Depends(get_db)
):
    """Obtener lista de docentes con filtros y paginación"""
    
    query = db.query(User).filter(User.role == RoleEnum.DOCENTE)
    
    # Aplicar filtros
    if search:
        search_filter = or_(
            User.first_name.ilike(f"%{search}%"),
            User.last_name.ilike(f"%{search}%"),
            User.dni.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if especialidad:
        query = query.filter(User.especialidad.ilike(f"%{especialidad}%"))
    
    # Contar total
    total = query.count()
    
    # Aplicar paginación
    docentes = query.offset(skip).limit(limit).all()
    
    return docentes

@router.get("/{docente_id}", response_model=UserResponse)
async def get_docente(
    docente_id: int,
    db: Session = Depends(get_db)
):
    """Obtener un docente específico por ID"""
    
    docente = db.query(User).filter(
        User.id == docente_id,
        User.role == RoleEnum.DOCENTE
    ).first()
    
    if not docente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docente no encontrado"
        )
    
    return docente

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_docente(
    docente_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Crear un nuevo docente"""
    
    # Validar que el rol sea docente
    if docente_data.role != RoleEnum.DOCENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol debe ser 'docente'"
        )
    
    # Verificar que no exista un usuario con el mismo DNI o email
    existing_user = db.query(User).filter(
        or_(User.dni == docente_data.dni, User.email == docente_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese DNI o email"
        )
    
    # Crear el docente
    hashed_password = get_password_hash(docente_data.password)
    
    new_docente = User(
        dni=docente_data.dni,
        first_name=docente_data.first_name,
        last_name=docente_data.last_name,
        email=docente_data.email,
        hashed_password=hashed_password,
        role=docente_data.role,
        phone=docente_data.phone,
        especialidad=docente_data.especialidad,
        grado_academico=docente_data.grado_academico,
        fecha_ingreso=docente_data.fecha_ingreso,
        is_active=docente_data.is_active
    )
    
    db.add(new_docente)
    db.commit()
    db.refresh(new_docente)
    
    return new_docente

@router.put("/{docente_id}", response_model=UserResponse)
async def update_docente(
    docente_id: int,
    docente_data: UserUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar un docente existente"""
    
    docente = db.query(User).filter(
        User.id == docente_id,
        User.role == RoleEnum.DOCENTE
    ).first()
    
    if not docente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docente no encontrado"
        )
    
    # Verificar email único si se está actualizando
    if docente_data.email and docente_data.email != docente.email:
        existing_user = db.query(User).filter(
            User.email == docente_data.email,
            User.id != docente_id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un usuario con ese email"
            )
    
    # Actualizar campos
    update_data = docente_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(docente, field, value)
    
    db.commit()
    db.refresh(docente)
    
    return docente

@router.delete("/{docente_id}")
def delete_docente(
    docente_id: int,
    db: Session = Depends(get_db)
):
    """Eliminar definitivamente un docente"""
    
    docente = db.query(User).filter(
        User.id == docente_id,
        User.role == RoleEnum.DOCENTE
    ).first()
    
    if not docente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docente no encontrado"
        )
    
    # Verificar si el docente tiene cursos asignados
    cursos_asignados = db.query(Curso).filter(
        Curso.docente_id == docente_id,
        Curso.is_active == True
    ).count()
    
    if cursos_asignados > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar el docente porque tiene {cursos_asignados} cursos asignados"
        )
    
    # Eliminar definitivamente
    db.delete(docente)
    db.commit()
    
    return {"message": "Docente eliminado definitivamente"}

@router.get("/{docente_id}/cursos", response_model=List[CursoResponse])
async def get_docente_cursos(
    docente_id: int,
    db: Session = Depends(get_db)
):
    """Obtener los cursos asignados a un docente"""
    
    docente = db.query(User).filter(
        User.id == docente_id,
        User.role == RoleEnum.DOCENTE
    ).first()
    
    if not docente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docente no encontrado"
        )
    
    cursos = db.query(Curso).options(
        joinedload(Curso.ciclo),
        joinedload(Curso.ciclo).joinedload("carrera")
    ).filter(
        Curso.docente_id == docente_id,
        Curso.is_active == True
    ).all()
    
    return {
        "docente": docente,
        "cursos": cursos,
        "total_cursos": len(cursos)
    }

@router.post("/{docente_id}/assign-curso", response_model=dict)
async def assign_curso_to_docente(
    docente_id: int,
    assignment: CursoAssignment,
    db: Session = Depends(get_db)
):
    """Asignar un curso a un docente"""
    
    docente = db.query(User).filter(
        User.id == docente_id,
        User.role == RoleEnum.DOCENTE
    ).first()
    
    if not docente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docente no encontrado"
        )
    
    cursos = db.query(Curso).options(
        joinedload(Curso.ciclo),
        joinedload(Curso.ciclo).joinedload("carrera")
    ).filter(
        Curso.docente_id == docente_id,
        Curso.is_active == True
    ).all()
    
    return {
        "docente": docente,
        "cursos": cursos,
        "total_cursos": len(cursos)
    }