from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from typing import List, Optional
from datetime import datetime, date

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ...shared.models import User, RoleEnum, Carrera, Ciclo, Curso, Matricula
from .schemas import MatriculaCreate, MatriculaUpdate, UserResponse

router = APIRouter(prefix="/matriculas", tags=["Admin - Matrículas"])

# ==================== CRUD MATRÍCULAS ====================

@router.get("/")
def get_matriculas(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    ciclo_id: Optional[int] = Query(None),
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
    
    # Removido filtro por curso_id ya que las matrículas no están directamente relacionadas con cursos
    # Los cursos están relacionados con ciclos, y las matrículas relacionan estudiantes con ciclos
    
    if estado:
        query = query.filter(Matricula.estado == estado)
    
    if is_active is not None:
        query = query.filter(Matricula.is_active == is_active)
    
    # Contar total
    total = query.count()
    
    # Aplicar paginación y ordenamiento
    matriculas = query.order_by(desc(Matricula.fecha_matricula)).offset(skip).limit(limit).all()
    
    # Formatear respuestas con información adicional
    matriculas_formateadas = []
    for matricula in matriculas:
        matricula_dict = {
            "id": matricula.id,
            "estudiante_id": matricula.estudiante_id,
            "ciclo_id": matricula.ciclo_id,
            "codigo_matricula": matricula.codigo_matricula,
            "fecha_matricula": matricula.fecha_matricula,
            "estado": matricula.estado,
            "is_active": matricula.is_active,
            # Información del estudiante
            "estudiante": {
                "id": matricula.estudiante.id if matricula.estudiante else None,
                "nombres": matricula.estudiante.first_name if matricula.estudiante else None,
                "apellidos": matricula.estudiante.last_name if matricula.estudiante else None,
                "dni": matricula.estudiante.dni if matricula.estudiante else None,
                "email": matricula.estudiante.email if matricula.estudiante else None,
                "carrera": {
                    "id": matricula.ciclo.carrera.id if matricula.ciclo and matricula.ciclo.carrera else None,
                    "nombre": matricula.ciclo.carrera.nombre if matricula.ciclo and matricula.ciclo.carrera else None
                } if matricula.ciclo and matricula.ciclo.carrera else None
            } if matricula.estudiante else None,
            # Información del ciclo
            "ciclo": {
                "id": matricula.ciclo.id if matricula.ciclo else None,
                "nombre": matricula.ciclo.nombre if matricula.ciclo else None,
                "descripcion": matricula.ciclo.descripcion if matricula.ciclo else None,
                "carrera_id": matricula.ciclo.carrera_id if matricula.ciclo else None
            } if matricula.ciclo else None,
            # Campos adicionales para compatibilidad
            "estudiante_nombre": f"{matricula.estudiante.first_name} {matricula.estudiante.last_name}" if matricula.estudiante else None,
            "ciclo_nombre": matricula.ciclo.nombre if matricula.ciclo else None,
            "carrera_nombre": matricula.ciclo.carrera.nombre if matricula.ciclo and matricula.ciclo.carrera else None
        }
        matriculas_formateadas.append(matricula_dict)
    
    return {
        "items": matriculas_formateadas,
        "total": total,
        "page": (skip // limit) + 1,
        "per_page": limit,
        "pages": (total + limit - 1) // limit
    }

@router.get("/{matricula_id}")
def get_matricula(
    matricula_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Obtener una matrícula específica"""
    
    matricula = db.query(Matricula).options(
        joinedload(Matricula.estudiante),
        joinedload(Matricula.ciclo).joinedload(Ciclo.carrera)
    ).filter(Matricula.id == matricula_id).first()
    
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Matrícula no encontrada"
        )
    
    # Formatear respuesta con información adicional
    matricula_formateada = {
        "id": matricula.id,
        "estudiante_id": matricula.estudiante_id,
        "ciclo_id": matricula.ciclo_id,
        "codigo_matricula": matricula.codigo_matricula,
        "fecha_matricula": matricula.fecha_matricula,
        "estado": matricula.estado,
        "is_active": matricula.is_active,
        # Información del estudiante
        "estudiante": {
            "id": matricula.estudiante.id if matricula.estudiante else None,
            "nombres": matricula.estudiante.first_name if matricula.estudiante else None,
            "apellidos": matricula.estudiante.last_name if matricula.estudiante else None,
            "dni": matricula.estudiante.dni if matricula.estudiante else None,
            "email": matricula.estudiante.email if matricula.estudiante else None,
            "carrera": {
                "id": matricula.ciclo.carrera.id if matricula.ciclo and matricula.ciclo.carrera else None,
                "nombre": matricula.ciclo.carrera.nombre if matricula.ciclo and matricula.ciclo.carrera else None
            } if matricula.ciclo and matricula.ciclo.carrera else None
        } if matricula.estudiante else None,
        # Información del ciclo
        "ciclo": {
            "id": matricula.ciclo.id if matricula.ciclo else None,
            "nombre": matricula.ciclo.nombre if matricula.ciclo else None,
            "descripcion": matricula.ciclo.descripcion if matricula.ciclo else None,
            "carrera_id": matricula.ciclo.carrera_id if matricula.ciclo else None
        } if matricula.ciclo else None,
        # Campos adicionales para compatibilidad
        "estudiante_nombre": f"{matricula.estudiante.first_name} {matricula.estudiante.last_name}" if matricula.estudiante else None,
        "ciclo_nombre": matricula.ciclo.nombre if matricula.ciclo else None,
        "carrera_nombre": matricula.ciclo.carrera.nombre if matricula.ciclo and matricula.ciclo.carrera else None
    }
    
    return matricula_formateada

@router.post("/")
def create_matricula(
    matricula_data: MatriculaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Crear una nueva matrícula"""
    
    # Verificar que el estudiante existe
    estudiante = db.query(User).filter(
        User.id == matricula_data.estudiante_id,
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
        Ciclo.id == matricula_data.ciclo_id,
        Ciclo.is_active == True
    ).first()
    
    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado o inactivo"
        )
    
    # Verificar que no existe una matrícula activa para el mismo estudiante y ciclo
    matricula_existente = db.query(Matricula).filter(
        Matricula.estudiante_id == matricula_data.estudiante_id,
        Matricula.ciclo_id == matricula_data.ciclo_id,
        Matricula.is_active == True
    ).first()
    
    if matricula_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estudiante ya está matriculado en este ciclo"
        )
    
    # Generar código único de matrícula
    import uuid
    codigo_matricula = f"MAT-{uuid.uuid4().hex[:8].upper()}"
    
    # Crear la matrícula
    nueva_matricula = Matricula(
        estudiante_id=matricula_data.estudiante_id,
        ciclo_id=matricula_data.ciclo_id,
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
    
    # Formatear respuesta con información adicional
    matricula_formateada = {
        "id": matricula_completa.id,
        "estudiante_id": matricula_completa.estudiante_id,
        "ciclo_id": matricula_completa.ciclo_id,
        "codigo_matricula": matricula_completa.codigo_matricula,
        "fecha_matricula": matricula_completa.fecha_matricula,
        "estado": matricula_completa.estado,
        "is_active": matricula_completa.is_active,
        # Información del estudiante
        "estudiante": {
            "id": matricula_completa.estudiante.id if matricula_completa.estudiante else None,
            "nombres": matricula_completa.estudiante.first_name if matricula_completa.estudiante else None,
            "apellidos": matricula_completa.estudiante.last_name if matricula_completa.estudiante else None,
            "dni": matricula_completa.estudiante.dni if matricula_completa.estudiante else None,
            "email": matricula_completa.estudiante.email if matricula_completa.estudiante else None,
            "carrera": {
                "id": matricula_completa.ciclo.carrera.id if matricula_completa.ciclo and matricula_completa.ciclo.carrera else None,
                "nombre": matricula_completa.ciclo.carrera.nombre if matricula_completa.ciclo and matricula_completa.ciclo.carrera else None
            } if matricula_completa.ciclo and matricula_completa.ciclo.carrera else None
        } if matricula_completa.estudiante else None,
        # Información del ciclo
        "ciclo": {
            "id": matricula_completa.ciclo.id if matricula_completa.ciclo else None,
            "nombre": matricula_completa.ciclo.nombre if matricula_completa.ciclo else None,
            "descripcion": matricula_completa.ciclo.descripcion if matricula_completa.ciclo else None,
            "carrera_id": matricula_completa.ciclo.carrera_id if matricula_completa.ciclo else None
        } if matricula_completa.ciclo else None,
        # Campos adicionales para compatibilidad
        "estudiante_nombre": f"{matricula_completa.estudiante.first_name} {matricula_completa.estudiante.last_name}" if matricula_completa.estudiante else None,
        "ciclo_nombre": matricula_completa.ciclo.nombre if matricula_completa.ciclo else None,
        "carrera_nombre": matricula_completa.ciclo.carrera.nombre if matricula_completa.ciclo and matricula_completa.ciclo.carrera else None
    }
    
    return matricula_formateada

@router.put("/{matricula_id}")
def update_matricula(
    matricula_id: int,
    matricula_data: MatriculaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Actualizar una matrícula (principalmente para cambiar estado)"""
    
    matricula = db.query(Matricula).filter(Matricula.id == matricula_id).first()
    
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Matrícula no encontrada"
        )
    
    # Actualizar campos
    matricula.is_active = matricula_data.is_active
    
    if not matricula_data.is_active:
        matricula.estado = "inactiva"
    else:
        matricula.estado = "activa"
    
    db.commit()
    db.refresh(matricula)
    
    # Cargar relaciones para la respuesta
    matricula_completa = db.query(Matricula).options(
        joinedload(Matricula.estudiante),
        joinedload(Matricula.curso),
        joinedload(Matricula.ciclo),
        joinedload(Matricula.carrera)
    ).filter(Matricula.id == matricula_id).first()
    
    return matricula_completa

@router.delete("/{matricula_id}")
def delete_matricula(
    matricula_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Desactivar una matrícula (soft delete)"""
    
    matricula = db.query(Matricula).filter(Matricula.id == matricula_id).first()
    
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Matrícula no encontrada"
        )
    
    # Desactivar matrícula
    matricula.is_active = False
    matricula.estado = "retirada"
    
    db.commit()
    
    return {"message": "Matrícula desactivada exitosamente"}

# ==================== ENDPOINTS ESPECÍFICOS ====================

@router.get("/estudiante/{estudiante_id}")
def get_matriculas_by_estudiante(
    estudiante_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Obtener todas las matrículas de un estudiante específico"""
    
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

@router.get("/cursos-disponibles/{ciclo_id}")
def get_cursos_disponibles_por_ciclo(
    ciclo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Obtener cursos disponibles para matrícula en un ciclo específico"""
    
    # Verificar que el ciclo existe
    ciclo = db.query(Ciclo).filter(
        Ciclo.id == ciclo_id,
        Ciclo.is_active == True
    ).first()
    
    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado o inactivo"
        )
    
    # Obtener cursos del ciclo
    cursos = db.query(Curso).options(
        joinedload(Curso.docente)
    ).filter(
        Curso.ciclo_id == ciclo_id,
        Curso.is_active == True
    ).order_by(Curso.nombre).all()
    
    # Formatear respuesta
    cursos_formateados = []
    for curso in cursos:
        curso_dict = {
            "id": curso.id,
            "nombre": curso.nombre,
            "codigo": curso.codigo,
            "creditos": curso.creditos,
            "horas_semanales": curso.horas_semanales,
            "ciclo_id": curso.ciclo_id,
            "docente_id": curso.docente_id,
            "docente_nombre": f"{curso.docente.first_name} {curso.docente.last_name}" if curso.docente else "Sin asignar",
            "is_active": curso.is_active
        }
        cursos_formateados.append(curso_dict)
    
    return {
        "ciclo": {
            "id": ciclo.id,
            "nombre": ciclo.nombre,
            "descripcion": ciclo.descripcion,
            "carrera_id": ciclo.carrera_id
        },
        "cursos": cursos_formateados,
        "total_cursos": len(cursos_formateados)
    }

@router.post("/matricular-estudiante-ciclo")
def matricular_estudiante_en_ciclo(
    estudiante_id: int,
    ciclo_id: int,
    cursos_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Matricular un estudiante en múltiples cursos de un ciclo"""
    
    # Verificar estudiante
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
    
    # Verificar ciclo
    ciclo = db.query(Ciclo).filter(
        Ciclo.id == ciclo_id,
        Ciclo.is_active == True
    ).first()
    
    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado o inactivo"
        )
    
    matriculas_creadas = []
    errores = []
    
    for curso_id in cursos_ids:
        # Verificar curso
        curso = db.query(Curso).filter(
            Curso.id == curso_id,
            Curso.ciclo_id == ciclo_id,
            Curso.is_active == True
        ).first()
        
        if not curso:
            errores.append(f"Curso con ID {curso_id} no encontrado o no pertenece al ciclo")
            continue
        
        # Verificar matrícula existente
        matricula_existente = db.query(Matricula).filter(
            Matricula.estudiante_id == estudiante_id,
            Matricula.curso_id == curso_id,
            Matricula.is_active == True
        ).first()
        
        if matricula_existente:
            errores.append(f"Ya matriculado en {curso.nombre}")
            continue
        
        # Crear matrícula
        nueva_matricula = Matricula(
            estudiante_id=estudiante_id,
            curso_id=curso_id,
            ciclo_id=ciclo_id,
            carrera_id=ciclo.carrera_id,
            fecha_matricula=date.today()
        )
        
        db.add(nueva_matricula)
        matriculas_creadas.append(curso.nombre)
    
    if matriculas_creadas:
        db.commit()
    
    return {
        "message": "Proceso de matrícula completado",
        "estudiante": f"{estudiante.first_name} {estudiante.last_name}",
        "ciclo": ciclo.nombre,
        "cursos_matriculados": matriculas_creadas,
        "errores": errores,
        "total_exitosas": len(matriculas_creadas),
        "total_errores": len(errores)
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
    
    # Extraer código de matrícula del cuerpo de la petición
    codigo_matricula = request_data.get('codigo_matricula', '')
    
    # Si no se proporciona código, generar uno automáticamente
    if not codigo_matricula or not codigo_matricula.strip():
        codigo_matricula = str(uuid.uuid4())
    
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
    
    # Verificar si ya existe una matrícula activa para este estudiante y ciclo
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
    
    # Obtener cursos del ciclo para información adicional
    cursos_ciclo = db.query(Curso).filter(
        Curso.ciclo_id == ciclo_id,
        Curso.is_active == True
    ).all()
    
    # Formatear respuesta con información adicional
    matricula_formateada = {
        "id": matricula_completa.id,
        "estudiante_id": matricula_completa.estudiante_id,
        "ciclo_id": matricula_completa.ciclo_id,
        "codigo_matricula": matricula_completa.codigo_matricula,
        "fecha_matricula": matricula_completa.fecha_matricula,
        "estado": matricula_completa.estado,
        "is_active": matricula_completa.is_active,
        # Información del estudiante
        "estudiante": {
            "id": matricula_completa.estudiante.id if matricula_completa.estudiante else None,
            "nombres": matricula_completa.estudiante.first_name if matricula_completa.estudiante else None,
            "apellidos": matricula_completa.estudiante.last_name if matricula_completa.estudiante else None,
            "dni": matricula_completa.estudiante.dni if matricula_completa.estudiante else None,
            "email": matricula_completa.estudiante.email if matricula_completa.estudiante else None,
            "carrera": {
                "id": matricula_completa.ciclo.carrera.id if matricula_completa.ciclo and matricula_completa.ciclo.carrera else None,
                "nombre": matricula_completa.ciclo.carrera.nombre if matricula_completa.ciclo and matricula_completa.ciclo.carrera else None
            } if matricula_completa.ciclo and matricula_completa.ciclo.carrera else None
        } if matricula_completa.estudiante else None,
        # Información del ciclo
        "ciclo": {
            "id": matricula_completa.ciclo.id if matricula_completa.ciclo else None,
            "nombre": matricula_completa.ciclo.nombre if matricula_completa.ciclo else None,
            "descripcion": matricula_completa.ciclo.descripcion if matricula_completa.ciclo else None,
            "carrera_id": matricula_completa.ciclo.carrera_id if matricula_completa.ciclo else None
        } if matricula_completa.ciclo else None,
        # Campos adicionales para compatibilidad
        "estudiante_nombre": f"{matricula_completa.estudiante.first_name} {matricula_completa.estudiante.last_name}" if matricula_completa.estudiante else None,
        "ciclo_nombre": matricula_completa.ciclo.nombre if matricula_completa.ciclo else None,
        "carrera_nombre": matricula_completa.ciclo.carrera.nombre if matricula_completa.ciclo and matricula_completa.ciclo.carrera else None
    }
    
    return {
        "message": "Matrícula creada exitosamente",
        "matricula": matricula_formateada,
        "cursos_disponibles": len(cursos_ciclo),
        "matriculas_creadas": 1  # Para compatibilidad con el cliente
    }