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

def get_ciclo_order(ciclo_nombre):
    """Convierte nombres de ciclos a números para ordenamiento"""
    if not ciclo_nombre:
        return 0
    
    # Mapeo de números romanos a enteros
    roman_to_int = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
        'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
    }
    
    # Extraer el número romano del nombre del ciclo
    ciclo_upper = ciclo_nombre.upper()
    for roman, num in sorted(roman_to_int.items(), key=lambda x: len(x[0]), reverse=True):
        if roman in ciclo_upper:
            return num
    
    return 0

# ==================== CRUD ESTUDIANTES ====================

@router.get("/")
def get_estudiantes(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=1000),
    search: Optional[str] = Query(None),
    ciclo_nombre: Optional[str] = Query(None, description="Filtrar por nombre de ciclo (I, II, III, IV, V, VI)"),
    estado_matricula: Optional[str] = Query(None, regex="^(matriculados|sin_matricular|todos)$", description="Filtrar por estado de matrícula: 'matriculados', 'sin_matricular', 'todos'"),
    db: Session = Depends(get_db)
):
    """Obtener lista de estudiantes activos, mostrando su ciclo más alto si están matriculados"""
    
    # Query base: todos los estudiantes activos ordenados por nombre
    query = db.query(User).options(
        joinedload(User.carrera),
        joinedload(User.estudiante_matriculas).joinedload(Matricula.ciclo)
    ).filter(
        User.role == RoleEnum.ESTUDIANTE,
        User.is_active == True
    ).order_by(User.last_name, User.first_name)
    
    # Aplicar filtros de búsqueda
    if search:
        search_filter = or_(
            User.first_name.ilike(f"%{search}%"),
            User.last_name.ilike(f"%{search}%"),
            User.dni.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Obtener todos los estudiantes (sin paginación inicial para procesar ciclos)
    estudiantes = query.all()
    
    # Procesar estudiantes para obtener su ciclo más alto
    estudiantes_procesados = []
    for estudiante in estudiantes:
        # Obtener todas las matrículas activas
        matriculas_activas = [m for m in estudiante.estudiante_matriculas if m.estado == "activa"]
        
        # Crear objeto estudiante base con solo los campos necesarios para el cliente
        estudiante_data = {
            "id": estudiante.id,
            "dni": estudiante.dni,
            "email": estudiante.email,
            "first_name": estudiante.first_name,
            "last_name": estudiante.last_name,
            "phone": estudiante.phone,
            "fecha_nacimiento": estudiante.fecha_nacimiento,
            "direccion": estudiante.direccion,
            "nombre_apoderado": estudiante.nombre_apoderado,
            "telefono_apoderado": estudiante.telefono_apoderado,
            "carrera": {
                "nombre": estudiante.carrera.nombre if estudiante.carrera else None
            } if estudiante.carrera else None,
        }
        
        if matriculas_activas:
            # Encontrar la matrícula con el ciclo más alto usando la función de ordenamiento
            matricula_ciclo_mayor = max(matriculas_activas, key=lambda m: (
                get_ciclo_order(m.ciclo.nombre) if get_ciclo_order(m.ciclo.nombre) > 0 else m.ciclo.numero
            ))
            
            # Agregar solo el ciclo actual que necesita el cliente
            estudiante_data["ciclo_actual"] = matricula_ciclo_mayor.ciclo.nombre
            estudiante_data["ciclo_actual_id"] = matricula_ciclo_mayor.ciclo_id
        else:
            # Estudiante sin matrículas activas
            estudiante_data["ciclo_actual"] = None
            estudiante_data["ciclo_actual_id"] = None
        
        estudiantes_procesados.append(estudiante_data)
    
    # Filtrar por estado de matrícula
    if estado_matricula:
        if estado_matricula == "matriculados":
            estudiantes_procesados = [e for e in estudiantes_procesados if e["ciclo_actual"] is not None]
        elif estado_matricula == "sin_matricular":
            estudiantes_procesados = [e for e in estudiantes_procesados if e["ciclo_actual"] is None]
        # Si es "todos", no filtrar
    
    # Filtrar por ciclo específico si se proporciona
    if ciclo_nombre:
        estudiantes_procesados = [e for e in estudiantes_procesados if e["ciclo_actual"] == ciclo_nombre]
    
    # Aplicar paginación
    total = len(estudiantes_procesados)
    offset = (page - 1) * per_page
    estudiantes_paginados = estudiantes_procesados[offset:offset + per_page]
    total_pages = (total + per_page - 1) // per_page
    
    return {
        "estudiantes": estudiantes_paginados,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_pagination": ciclo_nombre is None  # Indicador para el frontend
    }

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
    """Eliminar completamente un estudiante (hard delete)"""
    
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    # Eliminar completamente el estudiante
    db.delete(estudiante)
    db.commit()
    
    return {"message": "Estudiante eliminado exitosamente"}

@router.get("/search/dni/{dni}")
def search_estudiante_by_dni(
    dni: str,
    db: Session = Depends(get_db)
):
    """Buscar estudiante por DNI para matrícula"""
    
    # Validar formato de DNI
    if not dni or len(dni) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DNI debe tener al menos 8 dígitos"
        )
    
    # Buscar estudiante por DNI
    estudiante = db.query(User).options(
        joinedload(User.carrera)
    ).filter(
        User.dni == dni,
        User.role == RoleEnum.ESTUDIANTE,
        User.is_active == True
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ningún estudiante con ese DNI"
        )
    
    return {
        "id": estudiante.id,
        "dni": estudiante.dni,
        "first_name": estudiante.first_name,
        "last_name": estudiante.last_name,
        "email": estudiante.email,
        "phone": estudiante.phone,
        "fecha_nacimiento": estudiante.fecha_nacimiento,
        "direccion": estudiante.direccion,
        "nombre_apoderado": estudiante.nombre_apoderado,
        "telefono_apoderado": estudiante.telefono_apoderado,
        "carrera": {
            "nombre": estudiante.carrera.nombre
        } if estudiante.carrera else None
    }