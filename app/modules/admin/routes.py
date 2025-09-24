from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import math

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ..auth.security import get_password_hash
from .models import User, RoleEnum, Carrera, Ciclo, Curso, Matricula, Nota
from .schemas import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    CarreraCreate, CarreraUpdate, CarreraResponse,
    CicloCreate, CicloUpdate, CicloResponse,
    CursoCreate, CursoUpdate, CursoResponse,
    MatriculaCreate, MatriculaUpdate, MatriculaResponse,
    AdminDashboard, EstadisticasGenerales,
    FiltroUsuarios, FiltroCursos, FiltroMatriculas,
    OperacionMasivaUsuarios, ResultadoOperacionMasiva
)

router = APIRouter(prefix="/admin", tags=["Administrador"])

# ==================== DASHBOARD ====================
@router.get("/dashboard", response_model=AdminDashboard)
def get_admin_dashboard(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Obtener dashboard completo del administrador"""
    
    # Estadísticas generales
    total_usuarios = db.query(User).count()
    total_estudiantes = db.query(User).filter(User.role == RoleEnum.ESTUDIANTE).count()
    total_docentes = db.query(User).filter(User.role == RoleEnum.DOCENTE).count()
    total_admins = db.query(User).filter(User.role == RoleEnum.ADMIN).count()
    total_carreras = db.query(Carrera).filter(Carrera.is_active == True).count()
    total_ciclos = db.query(Ciclo).filter(Ciclo.is_active == True).count()
    total_cursos = db.query(Curso).filter(Curso.is_active == True).count()
    total_matriculas = db.query(Matricula).filter(Matricula.is_active == True).count()
    usuarios_activos = db.query(User).filter(User.is_active == True).count()
    usuarios_inactivos = db.query(User).filter(User.is_active == False).count()
    
    estadisticas = {
        "total_usuarios": total_usuarios,
        "total_estudiantes": total_estudiantes,
        "total_docentes": total_docentes,
        "total_admins": total_admins,
        "total_carreras": total_carreras,
        "total_ciclos": total_ciclos,
        "total_cursos": total_cursos,
        "total_matriculas": total_matriculas,
        "usuarios_activos": usuarios_activos,
        "usuarios_inactivos": usuarios_inactivos
    }
    
    # Usuarios recientes (últimos 10)
    usuarios_recientes = db.query(User).order_by(User.created_at.desc()).limit(10).all()
    
    # Actividad reciente del sistema
    actividad_sistema = []
    
    # Últimas matrículas
    matriculas_recientes = db.query(Matricula).options(
        joinedload(Matricula.estudiante),
        joinedload(Matricula.curso)
    ).order_by(Matricula.fecha_matricula.desc()).limit(5).all()
    
    for matricula in matriculas_recientes:
        actividad_sistema.append({
            "tipo": "matricula",
            "descripcion": f"{matricula.estudiante.nombres} {matricula.estudiante.apellidos} se matriculó en {matricula.curso.nombre}",
            "fecha": matricula.fecha_matricula,
            "usuario": f"{matricula.estudiante.nombres} {matricula.estudiante.apellidos}"
        })
    
    # Últimos usuarios creados
    usuarios_nuevos = db.query(User).order_by(User.created_at.desc()).limit(3).all()
    for usuario in usuarios_nuevos:
        actividad_sistema.append({
            "tipo": "usuario_creado",
            "descripcion": f"Nuevo usuario registrado: {usuario.nombres} {usuario.apellidos} ({usuario.role.value})",
            "fecha": usuario.created_at,
            "usuario": f"{usuario.nombres} {usuario.apellidos}"
        })
    
    # Ordenar actividad por fecha
    actividad_sistema.sort(key=lambda x: x["fecha"], reverse=True)
    actividad_sistema = actividad_sistema[:10]  # Limitar a 10 elementos
    
    # Alertas del sistema
    alertas = []
    
    # Verificar usuarios inactivos recientes
    if usuarios_inactivos > 0:
        alertas.append({
            "tipo": "warning",
            "titulo": "Usuarios inactivos",
            "mensaje": f"Hay {usuarios_inactivos} usuarios inactivos en el sistema",
            "fecha": datetime.utcnow()
        })
    
    # Verificar cursos sin docente
    cursos_sin_docente = db.query(Curso).filter(
        Curso.docente_id.is_(None),
        Curso.is_active == True
    ).count()
    
    if cursos_sin_docente > 0:
        alertas.append({
            "tipo": "error",
            "titulo": "Cursos sin docente",
            "mensaje": f"Hay {cursos_sin_docente} cursos activos sin docente asignado",
            "fecha": datetime.utcnow()
        })
    
    return {
        "estadisticas_generales": estadisticas,
        "usuarios_recientes": usuarios_recientes,
        "actividad_sistema": actividad_sistema,
        "alertas": alertas
    }

# ==================== GESTIÓN DE USUARIOS ====================
@router.get("/users", response_model=UserListResponse)
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    role: Optional[RoleEnum] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
):
    """Obtener lista de usuarios con filtros y paginación"""
    
    query = db.query(User)
    
    # Aplicar filtros
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                User.nombres.ilike(search_term),
                User.apellidos.ilike(search_term),
                User.dni.ilike(search_term),
                User.email.ilike(search_term)
            )
        )
    
    # Contar total
    total = query.count()
    
    # Aplicar paginación
    offset = (page - 1) * per_page
    users = query.offset(offset).limit(per_page).all()
    
    # Calcular total de páginas
    total_pages = math.ceil(total / per_page)
    
    return {
        "users": users,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }

@router.post("/users", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Crear un nuevo usuario"""
    
    # Verificar que el DNI no existe
    existing_user = db.query(User).filter(User.dni == user_data.dni).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con este DNI"
        )
    
    # Verificar que el email no existe
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con este email"
        )
    
    # Crear nuevo usuario
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        dni=user_data.dni,
        nombres=user_data.nombres,
        apellidos=user_data.apellidos,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role,
        telefono=user_data.telefono,
        direccion=user_data.direccion,
        fecha_nacimiento=user_data.fecha_nacimiento,
        is_active=user_data.is_active
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Obtener un usuario específico"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return user

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Actualizar un usuario"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar email único si se está actualizando
    if user_data.email and user_data.email != user.email:
        existing_email = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un usuario con este email"
            )
    
    # Actualizar campos
    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Eliminar un usuario (soft delete)"""
    
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propia cuenta"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Soft delete
    user.is_active = False
    db.commit()
    
    return {"message": "Usuario desactivado exitosamente"}

# ==================== GESTIÓN DE CARRERAS ====================
@router.get("/carreras", response_model=List[CarreraResponse])
def get_carreras(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    include_inactive: bool = Query(False)
):
    """Obtener lista de carreras"""
    
    query = db.query(Carrera)
    if not include_inactive:
        query = query.filter(Carrera.is_active == True)
    
    carreras = query.all()
    
    # Agregar información adicional
    carreras_response = []
    for carrera in carreras:
        total_cursos = db.query(Curso).filter(Curso.carrera_id == carrera.id).count()
        
        carrera_data = {
            "id": carrera.id,
            "nombre": carrera.nombre,
            "codigo": carrera.codigo,
            "descripcion": carrera.descripcion,
            "duracion_ciclos": carrera.duracion_ciclos,
            "is_active": carrera.is_active,
            "created_at": carrera.created_at,
            "total_cursos": total_cursos
        }
        carreras_response.append(carrera_data)
    
    return carreras_response

@router.post("/carreras", response_model=CarreraResponse)
def create_carrera(
    carrera_data: CarreraCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Crear una nueva carrera"""
    
    # Verificar que el código no existe
    existing_carrera = db.query(Carrera).filter(Carrera.codigo == carrera_data.codigo).first()
    if existing_carrera:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una carrera con este código"
        )
    
    new_carrera = Carrera(**carrera_data.dict())
    db.add(new_carrera)
    db.commit()
    db.refresh(new_carrera)
    
    return new_carrera

@router.put("/carreras/{carrera_id}", response_model=CarreraResponse)
def update_carrera(
    carrera_id: int,
    carrera_data: CarreraUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Actualizar una carrera"""
    
    carrera = db.query(Carrera).filter(Carrera.id == carrera_id).first()
    if not carrera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrera no encontrada"
        )
    
    # Verificar código único si se está actualizando
    if carrera_data.codigo and carrera_data.codigo != carrera.codigo:
        existing_codigo = db.query(Carrera).filter(
            Carrera.codigo == carrera_data.codigo,
            Carrera.id != carrera_id
        ).first()
        if existing_codigo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una carrera con este código"
            )
    
    # Actualizar campos
    update_data = carrera_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(carrera, field, value)
    
    db.commit()
    db.refresh(carrera)
    
    return carrera

# ==================== GESTIÓN DE CICLOS ====================
@router.get("/ciclos", response_model=List[CicloResponse])
def get_ciclos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    include_inactive: bool = Query(False)
):
    """Obtener lista de ciclos"""
    
    query = db.query(Ciclo)
    if not include_inactive:
        query = query.filter(Ciclo.is_active == True)
    
    ciclos = query.order_by(Ciclo.fecha_inicio.desc()).all()
    
    # Agregar información adicional
    ciclos_response = []
    for ciclo in ciclos:
        total_cursos = db.query(Curso).filter(Curso.ciclo_id == ciclo.id).count()
        total_matriculas = db.query(Matricula).filter(Matricula.ciclo_id == ciclo.id).count()
        
        ciclo_data = {
            "id": ciclo.id,
            "nombre": ciclo.nombre,
            "fecha_inicio": ciclo.fecha_inicio,
            "fecha_fin": ciclo.fecha_fin,
            "fecha_cierre_notas": ciclo.fecha_cierre_notas,
            "is_active": ciclo.is_active,
            "created_at": ciclo.created_at,
            "total_cursos": total_cursos,
            "total_matriculas": total_matriculas
        }
        ciclos_response.append(ciclo_data)
    
    return ciclos_response

@router.post("/ciclos", response_model=CicloResponse)
def create_ciclo(
    ciclo_data: CicloCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Crear un nuevo ciclo"""
    
    new_ciclo = Ciclo(**ciclo_data.dict())
    db.add(new_ciclo)
    db.commit()
    db.refresh(new_ciclo)
    
    return new_ciclo

# ==================== GESTIÓN DE CURSOS ====================
@router.get("/cursos", response_model=List[CursoResponse])
def get_cursos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    carrera_id: Optional[int] = None,
    ciclo_id: Optional[int] = None,
    docente_id: Optional[int] = None,
    include_inactive: bool = Query(False)
):
    """Obtener lista de cursos con filtros"""
    
    query = db.query(Curso).options(
        joinedload(Curso.carrera),
        joinedload(Curso.ciclo),
        joinedload(Curso.docente)
    )
    
    if not include_inactive:
        query = query.filter(Curso.is_active == True)
    if carrera_id:
        query = query.filter(Curso.carrera_id == carrera_id)
    if ciclo_id:
        query = query.filter(Curso.ciclo_id == ciclo_id)
    if docente_id:
        query = query.filter(Curso.docente_id == docente_id)
    
    cursos = query.all()
    
    # Convertir a formato de respuesta
    cursos_response = []
    for curso in cursos:
        total_matriculados = db.query(Matricula).filter(
            Matricula.curso_id == curso.id,
            Matricula.is_active == True
        ).count()
        
        curso_data = {
            "id": curso.id,
            "nombre": curso.nombre,
            "codigo": curso.codigo,
            "creditos": curso.creditos,
            "horas_semanales": curso.horas_semanales,
            "carrera_id": curso.carrera_id,
            "ciclo_id": curso.ciclo_id,
            "docente_id": curso.docente_id,
            "horario": curso.horario,
            "aula": curso.aula,
            "max_estudiantes": curso.max_estudiantes,
            "is_active": curso.is_active,
            "created_at": curso.created_at,
            "carrera_nombre": curso.carrera.nombre,
            "ciclo_nombre": curso.ciclo.nombre,
            "docente_nombre": f"{curso.docente.nombres} {curso.docente.apellidos}" if curso.docente else None,
            "total_matriculados": total_matriculados
        }
        cursos_response.append(curso_data)
    
    return cursos_response

@router.post("/cursos", response_model=CursoResponse)
def create_curso(
    curso_data: CursoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Crear un nuevo curso"""
    
    # Verificar que la carrera existe
    carrera = db.query(Carrera).filter(Carrera.id == curso_data.carrera_id).first()
    if not carrera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrera no encontrada"
        )
    
    # Verificar que el ciclo existe
    ciclo = db.query(Ciclo).filter(Ciclo.id == curso_data.ciclo_id).first()
    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado"
        )
    
    # Verificar que el docente existe y es docente
    docente = db.query(User).filter(
        User.id == curso_data.docente_id,
        User.role.in_([RoleEnum.DOCENTE, RoleEnum.ADMIN])
    ).first()
    if not docente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docente no encontrado o no tiene permisos para enseñar"
        )
    
    new_curso = Curso(**curso_data.dict())
    db.add(new_curso)
    db.commit()
    db.refresh(new_curso)
    
    return new_curso

# ==================== OPERACIONES MASIVAS ====================
@router.post("/users/bulk-operation", response_model=ResultadoOperacionMasiva)
def bulk_user_operation(
    operacion: OperacionMasivaUsuarios,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Realizar operaciones masivas en usuarios"""
    
    exitosos = 0
    fallidos = 0
    errores = []
    
    for user_id in operacion.user_ids:
        try:
            if user_id == current_user.id and operacion.accion in ["deactivate", "delete"]:
                errores.append(f"No puedes {operacion.accion} tu propia cuenta")
                fallidos += 1
                continue
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                errores.append(f"Usuario {user_id} no encontrado")
                fallidos += 1
                continue
            
            if operacion.accion == "activate":
                user.is_active = True
            elif operacion.accion == "deactivate":
                user.is_active = False
            elif operacion.accion == "delete":
                user.is_active = False  # Soft delete
            
            exitosos += 1
            
        except Exception as e:
            errores.append(f"Error con usuario {user_id}: {str(e)}")
            fallidos += 1
    
    if exitosos > 0:
        db.commit()
    
    return {
        "exitosos": exitosos,
        "fallidos": fallidos,
        "errores": errores,
        "mensaje": f"Operación completada: {exitosos} exitosos, {fallidos} fallidos"
    }