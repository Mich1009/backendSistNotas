from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from typing import List, Optional
from datetime import datetime, date
import uuid
import re

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ...shared.models import User, RoleEnum, Carrera, Ciclo, Curso, Matricula
from .schemas import MatriculaCreate, MatriculaUpdate, UserResponse

router = APIRouter(prefix="/matriculas", tags=["Admin - Matrículas"])

# ==================== FUNCIONES AUXILIARES ====================

def get_ciclo_order(ciclo_nombre: str) -> int:
    """
    Convierte el nombre del ciclo (I, II, III, IV, V, VI) a un número entero para ordenamiento.
    Retorna 0 si no se puede determinar el orden.
    """
    roman_to_int = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6,
        'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
    }
    
    # Extraer solo los números romanos del nombre del ciclo
    roman_match = re.search(r'\b(I{1,3}|IV|V|VI{0,3}|IX|X)\b', ciclo_nombre.upper())
    if roman_match:
        roman_numeral = roman_match.group(1)
        return roman_to_int.get(roman_numeral, 0)
    
    return 0

def validate_sequential_enrollment(estudiante_id: int, ciclo_id: int, db: Session) -> None:
    """
    Valida que el estudiante pueda matricularse en el ciclo especificado sin saltarse ciclos.
    Lanza HTTPException si la validación falla.
    """
    # Obtener el ciclo al que se quiere matricular
    ciclo_objetivo = db.query(Ciclo).filter(Ciclo.id == ciclo_id).first()
    if not ciclo_objetivo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado"
        )
    
    # Obtener el estudiante y su carrera
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE
    ).first()
    
    if not estudiante or not estudiante.carrera_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estudiante no encontrado o no tiene carrera asignada"
        )
    
    # Verificar que el ciclo pertenece a la misma carrera del estudiante
    if ciclo_objetivo.carrera_id != estudiante.carrera_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ciclo no pertenece a la carrera del estudiante"
        )
    
    # Obtener el orden del ciclo objetivo
    orden_objetivo = get_ciclo_order(ciclo_objetivo.nombre)
    if orden_objetivo == 0:
        # Si no se puede determinar el orden, permitir la matrícula (para casos especiales)
        return
    
    # Si es el primer ciclo (I), siempre se puede matricular
    if orden_objetivo == 1:
        return
    
    # Obtener todos los ciclos de la carrera del estudiante
    ciclos_carrera = db.query(Ciclo).filter(
        Ciclo.carrera_id == estudiante.carrera_id,
        Ciclo.is_active == True
    ).all()
    
    # Obtener las matrículas activas del estudiante en esta carrera
    matriculas_estudiante = db.query(Matricula).join(Ciclo).filter(
        Matricula.estudiante_id == estudiante_id,
        Matricula.is_active == True,
        Ciclo.carrera_id == estudiante.carrera_id
    ).all()
    
    # Obtener los ciclos en los que ya está matriculado
    ciclos_matriculados = set()
    for matricula in matriculas_estudiante:
        ciclo = db.query(Ciclo).filter(Ciclo.id == matricula.ciclo_id).first()
        if ciclo:
            orden_ciclo = get_ciclo_order(ciclo.nombre)
            if orden_ciclo > 0:
                ciclos_matriculados.add(orden_ciclo)
    
    # Verificar que ha completado todos los ciclos anteriores
    for orden_requerido in range(1, orden_objetivo):
        if orden_requerido not in ciclos_matriculados:
            # Buscar el nombre del ciclo faltante
            ciclo_faltante = None
            for ciclo in ciclos_carrera:
                if get_ciclo_order(ciclo.nombre) == orden_requerido:
                    ciclo_faltante = ciclo.nombre
                    break
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede matricular en el ciclo {ciclo_objetivo.nombre}. "
                       f"Debe completar primero el ciclo {ciclo_faltante or 'anterior'}"
            )

# ==================== CRUD MATRÍCULAS ====================

@router.get("/")
def get_matriculas(
    skip: int = Query(0, ge=0),
    limit: int = Query(5000, ge=1, le=5000),
    search: Optional[str] = Query(None),
    ciclo_id: Optional[int] = Query(None),
    año: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Obtener todas las matrículas con filtros"""
    
    query = db.query(Matricula).options(
        joinedload(Matricula.estudiante),
        joinedload(Matricula.ciclo).joinedload(Ciclo.carrera)
    )
    
    # Aplicar filtros
    if search:
        query = query.join(User, Matricula.estudiante_id == User.id).filter(
            or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.dni.ilike(f"%{search}%")
            )
        )
    
    if ciclo_id:
        query = query.filter(Matricula.ciclo_id == ciclo_id)
    
    # Filtrar por año del ciclo
    if año:
        query = query.join(Ciclo, Matricula.ciclo_id == Ciclo.id).filter(Ciclo.año == año)
    
    # Removido filtro por curso_id ya que las matrículas no están directamente relacionadas con cursos
    # Los cursos están relacionados con ciclos, y las matrículas relacionan estudiantes con ciclos
    
    if estado:
        query = query.filter(Matricula.estado == estado)
    
    if is_active is not None:
        query = query.filter(Matricula.is_active == is_active)
    
    # Contar total
    total = query.count()
    
    # Aplicar paginación y ordenamiento por número de ciclo, apellidos y nombres
    matriculas = query.join(User, Matricula.estudiante_id == User.id).join(
        Ciclo, Matricula.ciclo_id == Ciclo.id
    ).order_by(
        Ciclo.numero.asc(),  # Primero por número de ciclo
        User.last_name.asc(), 
        User.first_name.asc()
    ).offset(skip).limit(limit).all()
    
    # Formatear respuestas con información adicional
    matriculas_formateadas = []
    for matricula in matriculas:
        matricula_dict = {
            "id": matricula.id,
            "ciclo_id": matricula.ciclo_id,
            "codigo_matricula": matricula.codigo_matricula,
            "fecha_matricula": matricula.fecha_matricula,
            "is_active": matricula.is_active,
            # Información del estudiante (solo campos necesarios)
            "estudiante": {
                "nombres": matricula.estudiante.first_name if matricula.estudiante else None,
                "apellidos": matricula.estudiante.last_name if matricula.estudiante else None,
                "dni": matricula.estudiante.dni if matricula.estudiante else None,
                "carrera": {
                    "nombre": matricula.ciclo.carrera.nombre if matricula.ciclo and matricula.ciclo.carrera else None
                } if matricula.ciclo and matricula.ciclo.carrera else None
            } if matricula.estudiante else None,
            # Información del ciclo (solo campos necesarios)
            "ciclo": {
                "nombre": matricula.ciclo.nombre if matricula.ciclo else None,
                "numero": matricula.ciclo.numero if matricula.ciclo else None,
                "año": matricula.ciclo.año if matricula.ciclo else None
            } if matricula.ciclo else None
        }
        matriculas_formateadas.append(matricula_dict)
    
    return {
        "items": matriculas_formateadas,
        "total": total,
        "page": (skip // limit) + 1,
        "per_page": limit,
        "pages": (total + limit - 1) // limit
    }

@router.delete("/{matricula_id}")
def delete_matricula(
    matricula_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Eliminar completamente una matrícula (hard delete)"""
    
    matricula = db.query(Matricula).filter(Matricula.id == matricula_id).first()
    
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Matrícula no encontrada"
        )
    
    # Eliminar completamente la matrícula
    db.delete(matricula)
    db.commit()
    
    return {"message": "Matrícula eliminada exitosamente"}

# ==================== ENDPOINTS ESPECÍFICOS ====================

@router.get("/ciclos-disponibles/{estudiante_id}")
def get_ciclos_disponibles_para_estudiante(
    estudiante_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Obtener ciclos disponibles para matrícula de un estudiante específico según su progreso secuencial"""
    
    # Verificar que el estudiante existe y está activo
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE,
        User.is_active == True
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado o inactivo"
        )
    
    if not estudiante.carrera_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estudiante no tiene carrera asignada"
        )
    
    # Obtener todos los ciclos de la carrera del estudiante
    ciclos_carrera = db.query(Ciclo).filter(
        Ciclo.carrera_id == estudiante.carrera_id,
        Ciclo.is_active == True
    ).order_by(Ciclo.id).all()
    
    # Obtener las matrículas activas del estudiante en esta carrera
    matriculas_estudiante = db.query(Matricula).join(Ciclo).filter(
        Matricula.estudiante_id == estudiante_id,
        Matricula.is_active == True,
        Ciclo.carrera_id == estudiante.carrera_id
    ).all()
    
    # Obtener los ciclos en los que ya está matriculado
    ciclos_matriculados = set()
    for matricula in matriculas_estudiante:
        ciclo = db.query(Ciclo).filter(Ciclo.id == matricula.ciclo_id).first()
        if ciclo:
            orden_ciclo = get_ciclo_order(ciclo.nombre)
            if orden_ciclo > 0:
                ciclos_matriculados.add(orden_ciclo)
    
    # Determinar el siguiente ciclo disponible
    ciclos_disponibles = []
    
    for ciclo in ciclos_carrera:
        orden_ciclo = get_ciclo_order(ciclo.nombre)
        
        # Si no se puede determinar el orden, incluir el ciclo (para casos especiales)
        if orden_ciclo == 0:
            ciclos_disponibles.append({
                "id": ciclo.id,
                "nombre": ciclo.nombre,
                "descripcion": ciclo.descripcion,
                "fecha_inicio": ciclo.fecha_inicio.isoformat() if ciclo.fecha_inicio else None,
                "fecha_fin": ciclo.fecha_fin.isoformat() if ciclo.fecha_fin else None,
                "carrera_id": ciclo.carrera_id,
                "año": ciclo.año,
                "is_active": ciclo.is_active,
                "puede_matricularse": True,
                "razon": "Ciclo especial"
            })
            continue
        
        # Verificar si ya está matriculado en este ciclo
        if orden_ciclo in ciclos_matriculados:
            ciclos_disponibles.append({
                "id": ciclo.id,
                "nombre": ciclo.nombre,
                "descripcion": ciclo.descripcion,
                "fecha_inicio": ciclo.fecha_inicio.isoformat() if ciclo.fecha_inicio else None,
                "fecha_fin": ciclo.fecha_fin.isoformat() if ciclo.fecha_fin else None,
                "carrera_id": ciclo.carrera_id,
                "año": ciclo.año,
                "is_active": ciclo.is_active,
                "puede_matricularse": False,
                "razon": "Ya matriculado en este ciclo"
            })
            continue
        
        # Verificar si puede matricularse (ha completado todos los ciclos anteriores)
        puede_matricularse = True
        razon = "Disponible para matrícula"
        
        if orden_ciclo > 1:  # Si no es el primer ciclo
            for orden_requerido in range(1, orden_ciclo):
                if orden_requerido not in ciclos_matriculados:
                    puede_matricularse = False
                    # Buscar el nombre del ciclo faltante
                    ciclo_faltante = None
                    for c in ciclos_carrera:
                        if get_ciclo_order(c.nombre) == orden_requerido:
                            ciclo_faltante = c.nombre
                            break
                    razon = f"Debe completar primero el ciclo {ciclo_faltante or 'anterior'}"
                    break
        
        ciclos_disponibles.append({
            "id": ciclo.id,
            "nombre": ciclo.nombre,
            "descripcion": ciclo.descripcion,
            "fecha_inicio": ciclo.fecha_inicio.isoformat() if ciclo.fecha_inicio else None,
            "fecha_fin": ciclo.fecha_fin.isoformat() if ciclo.fecha_fin else None,
            "carrera_id": ciclo.carrera_id,
            "año": ciclo.año,
            "is_active": ciclo.is_active,
            "puede_matricularse": puede_matricularse,
            "razon": razon
        })
    
    return {
        "estudiante": {
            "id": estudiante.id,
            "nombres": f"{estudiante.first_name} {estudiante.last_name}",
            "dni": estudiante.dni,
            "carrera": estudiante.carrera.nombre if estudiante.carrera else None
        },
        "ciclos_disponibles": ciclos_disponibles,
        "total_ciclos": len(ciclos_disponibles),
        "ciclos_matriculados": len(ciclos_matriculados)
    }

@router.post("/estudiante/{estudiante_id}/ciclo/{ciclo_id}")
def matricular_estudiante_ciclo(
    estudiante_id: int,
    ciclo_id: int,
    request_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Matricular un estudiante en un ciclo específico"""
    
    # Extraer y normalizar código de matrícula
    codigo_matricula = (request_data.get('codigo_matricula', '') or '').strip()
    
    # Si no se proporciona código, generar uno automáticamente
    if not codigo_matricula:
        import uuid
        codigo_matricula = f"MAT-{uuid.uuid4().hex[:8].upper()}"
    
    # Verificar que el estudiante existe y está activo
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE,
        User.is_active == True
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado o inactivo"
        )
    
    # Verificar que el ciclo existe y está activo
    ciclo = db.query(Ciclo).filter(
        Ciclo.id == ciclo_id,
        Ciclo.is_active == True
    ).first()
    
    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado o inactivo"
        )
    
    # VALIDACIÓN SECUENCIAL: Verificar que el estudiante puede matricularse en este ciclo
    validate_sequential_enrollment(estudiante_id, ciclo_id, db)
    
    # Verificar que no existe una matrícula activa para el mismo estudiante y ciclo
    matricula_existente = db.query(Matricula).filter(
        Matricula.estudiante_id == estudiante_id,
        Matricula.ciclo_id == ciclo_id,
        Matricula.is_active == True
    ).first()
    
    if matricula_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estudiante ya está matriculado en este ciclo"
        )
    
    # Crear la matrícula
    nueva_matricula = Matricula(
        estudiante_id=estudiante_id,
        ciclo_id=ciclo_id,
        codigo_matricula=codigo_matricula,
        fecha_matricula=date.today()
    )
    
    db.add(nueva_matricula)
    db.commit()
    db.refresh(nueva_matricula)
    
    # Cargar relaciones para la respuesta
    matricula_completa = db.query(Matricula).options(
        joinedload(Matricula.estudiante),
        joinedload(Matricula.ciclo).joinedload(Ciclo.carrera)
    ).filter(Matricula.id == nueva_matricula.id).first()
    
    return {
        "message": "Matrícula creada exitosamente",
        "matricula": {
            "id": matricula_completa.id,
            "estudiante_id": matricula_completa.estudiante_id,
            "ciclo_id": matricula_completa.ciclo_id,
            "codigo_matricula": matricula_completa.codigo_matricula,
            "fecha_matricula": matricula_completa.fecha_matricula,
            "estado": matricula_completa.estado,
            "is_active": matricula_completa.is_active,
            "estudiante": {
                "id": matricula_completa.estudiante.id,
                "nombres": matricula_completa.estudiante.first_name,
                "apellidos": matricula_completa.estudiante.last_name,
                "dni": matricula_completa.estudiante.dni,
                "email": matricula_completa.estudiante.email
            },
            "ciclo": {
                "id": matricula_completa.ciclo.id,
                "nombre": matricula_completa.ciclo.nombre,
                "carrera": {
                    "id": matricula_completa.ciclo.carrera.id,
                    "nombre": matricula_completa.ciclo.carrera.nombre
                }
            }
        }
    }