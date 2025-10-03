from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from typing import List, Optional
from datetime import datetime

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ..auth.security import get_password_hash
from ...shared.models import User, RoleEnum, Matricula, Nota, Ciclo, Curso, Carrera
from .schemas import UserCreate, UserUpdate, UserResponse, UserListResponse

router = APIRouter(prefix="/estudiantes", tags=["Admin - Estudiantes"])

# ==================== CRUD ESTUDIANTES ====================

@router.get("/", response_model=UserListResponse)
def get_estudiantes(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    ciclo_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Obtener lista de estudiantes con filtros y paginación"""
    
    query = db.query(User).options(joinedload(User.carrera)).filter(User.role == RoleEnum.ESTUDIANTE)
    
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
    
    if ciclo_id:
        # Filtrar estudiantes matriculados en un ciclo específico
        query = query.join(Matricula).filter(
            Matricula.ciclo_id == ciclo_id,
            Matricula.estado == "activa"
        )
    
    # Contar total
    total = query.count()
    
    # Aplicar paginación
    offset = (page - 1) * per_page
    estudiantes = query.offset(offset).limit(per_page).all()
    
    # Calcular páginas totales
    total_pages = (total + per_page - 1) // per_page
    
    return {
        "users": estudiantes,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }

@router.get("/{estudiante_id}", response_model=UserResponse)
def get_estudiante(
    estudiante_id: int,
    db: Session = Depends(get_db)
):
    """Obtener un estudiante por ID"""
    
    estudiante = db.query(User).options(joinedload(User.carrera)).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    return estudiante

@router.post("/", response_model=UserResponse)
def create_estudiante(
    estudiante_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Crear un nuevo estudiante"""
    
    # Validar que el rol sea estudiante
    if estudiante_data.role != RoleEnum.ESTUDIANTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol debe ser 'estudiante'"
        )
    
    # Verificar que no exista un usuario con el mismo DNI o email
    existing_user = db.query(User).filter(
        or_(User.dni == estudiante_data.dni, User.email == estudiante_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese DNI o email"
        )
    
    # Obtener la carrera por defecto (la primera carrera activa)
    carrera_default = db.query(Carrera).filter(Carrera.is_active == True).first()
    
    if not carrera_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay carreras disponibles en el sistema"
        )
    
    # Crear el estudiante
    hashed_password = get_password_hash(estudiante_data.password)
    
    new_estudiante = User(
        dni=estudiante_data.dni,
        first_name=estudiante_data.first_name,
        last_name=estudiante_data.last_name,
        email=estudiante_data.email,
        hashed_password=hashed_password,
        role=estudiante_data.role,
        phone=estudiante_data.phone,
        fecha_nacimiento=estudiante_data.fecha_nacimiento,
        direccion=estudiante_data.direccion,
        nombre_apoderado=estudiante_data.nombre_apoderado,
        telefono_apoderado=estudiante_data.telefono_apoderado,
        carrera_id=carrera_default.id,  # Asignar carrera por defecto
        is_active=estudiante_data.is_active
    )
    
    db.add(new_estudiante)
    db.commit()
    db.refresh(new_estudiante)
    
    return new_estudiante

@router.put("/{estudiante_id}", response_model=UserResponse)
def update_estudiante(
    estudiante_id: int,
    estudiante_data: UserUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar un estudiante existente"""
    
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    # Verificar email único si se está actualizando
    if estudiante_data.email and estudiante_data.email != estudiante.email:
        existing_user = db.query(User).filter(
            User.email == estudiante_data.email,
            User.id != estudiante_id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un usuario con ese email"
            )
    
    # Actualizar campos
    update_data = estudiante_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(estudiante, field, value)
    
    db.commit()
    db.refresh(estudiante)
    
    return estudiante

@router.delete("/{estudiante_id}")
def delete_estudiante(
    estudiante_id: int,
    db: Session = Depends(get_db)
):
    """Eliminar (desactivar) un estudiante"""
    
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    # Verificar si el estudiante tiene matrículas activas
    matriculas_activas = db.query(Matricula).filter(
        Matricula.estudiante_id == estudiante_id,
        Matricula.estado == "activa"
    ).count()
    
    if matriculas_activas > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar el estudiante porque tiene {matriculas_activas} matrículas activas"
        )
    
    # Desactivar en lugar de eliminar
    estudiante.is_active = False
    db.commit()
    
    return {"message": "Estudiante desactivado exitosamente"}

@router.get("/{estudiante_id}/notas")
def get_estudiante_notas(
    estudiante_id: int,
    ciclo_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Obtener las notas de un estudiante, opcionalmente filtradas por ciclo"""
    
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    query = db.query(Nota).options(
        joinedload(Nota.curso),
        joinedload(Nota.curso).joinedload(Curso.ciclo)
    ).filter(Nota.estudiante_id == estudiante_id)
    
    if ciclo_id:
        query = query.join(Curso).filter(Curso.ciclo_id == ciclo_id)
    
    notas = query.all()
    
    # Calcular promedio por ciclo
    promedios_por_ciclo = {}
    for nota in notas:
        ciclo = nota.curso.ciclo.id
        if ciclo not in promedios_por_ciclo:
            promedios_por_ciclo[ciclo] = {
                "ciclo_nombre": nota.curso.ciclo.nombre,
                "notas": [],
                "promedio": 0
            }
        promedios_por_ciclo[ciclo]["notas"].append(float(nota.nota))
    
    # Calcular promedios
    for ciclo_id, data in promedios_por_ciclo.items():
        if data["notas"]:
            data["promedio"] = sum(data["notas"]) / len(data["notas"])
    
    return {
        "estudiante": estudiante,
        "notas": notas,
        "promedios_por_ciclo": promedios_por_ciclo,
        "total_notas": len(notas)
    }

@router.get("/{estudiante_id}/matriculas")
def get_estudiante_matriculas(
    estudiante_id: int,
    db: Session = Depends(get_db)
):
    """Obtener las matrículas de un estudiante"""
    
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    matriculas = db.query(Matricula).options(
        joinedload(Matricula.curso),
        joinedload(Matricula.ciclo),
        joinedload(Matricula.carrera)
    ).filter(
        Matricula.estudiante_id == estudiante_id
    ).order_by(desc(Matricula.fecha_matricula)).all()
    
    return {
        "estudiante": estudiante,
        "matriculas": matriculas,
        "total_matriculas": len(matriculas)
    }

@router.post("/{estudiante_id}/activate")
def activate_estudiante(
    estudiante_id: int,
    db: Session = Depends(get_db)
):
    """Activar un estudiante desactivado"""
    
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    estudiante.is_active = True
    db.commit()
    
    return {"message": "Estudiante activado exitosamente"}

@router.get("/search/dni/{dni}")
def search_estudiante_by_dni(
    dni: str,
    db: Session = Depends(get_db)
):
    """Buscar estudiante por DNI"""
    
    estudiante = db.query(User).options(joinedload(User.carrera)).filter(
        User.dni == dni,
        User.role == RoleEnum.ESTUDIANTE,
        User.is_active == True
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    return {
        "id": estudiante.id,
        "dni": estudiante.dni,
        "email": estudiante.email,
        "first_name": estudiante.first_name,
        "last_name": estudiante.last_name,
        "full_name": estudiante.full_name,
        "phone": estudiante.phone,
        "fecha_nacimiento": estudiante.fecha_nacimiento,
        "direccion": estudiante.direccion,
        "nombre_apoderado": estudiante.nombre_apoderado,
        "telefono_apoderado": estudiante.telefono_apoderado,
        "carrera_id": estudiante.carrera_id,
        "carrera": estudiante.carrera,
        "is_active": estudiante.is_active,
        "created_at": estudiante.created_at
    }