from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import math

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ..auth.security import get_password_hash
from .models import User, RoleEnum, Carrera, Ciclo, Curso, Matricula, Nota, Estudiante, HistorialNota
from .schemas import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    CarreraCreate, CarreraUpdate, CarreraResponse,
    CicloCreate, CicloUpdate, CicloResponse,
    CursoCreate, CursoUpdate, CursoResponse,
    MatriculaCreate, MatriculaUpdate, MatriculaResponse,
    NotaCreate, NotaUpdate, NotaResponse, HistorialNotaResponse,
    AdminDashboard, EstadisticasGenerales,
    FiltroUsuarios, FiltroCursos, FiltroMatriculas,
    OperacionMasivaUsuarios, ResultadoOperacionMasiva,
    EstudianteResponse, EstudianteCreate, EstudianteUpdate, OperacionMasivaEstudiantes,
    OperacionMasivaCarreras, OperacionMasivaCiclos, OperacionMasivaCursos,
    OperacionMasivaMatriculas
)

router = APIRouter(prefix="/admin", tags=["Administrador"])

# ==================== DASHBOARD ====================
@router.get("/dashboard", response_model=AdminDashboard)
def get_admin_dashboard(
    #current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Obtener dashboard completo del administrador"""
    
    # Estadísticas generales
    total_usuarios = db.query(User).count()
    total_estudiantes = db.query(Estudiante).count()
    total_docentes = db.query(User).filter(User.role == RoleEnum.DOCENTE).count()
    total_admins = db.query(User).filter(User.role == RoleEnum.ADMIN).count()
    total_carreras = db.query(Carrera).filter(Carrera.is_active == True).count()
    total_ciclos = db.query(Ciclo).filter(Ciclo.is_active == True).count()
    total_cursos = db.query(Curso).filter(Curso.is_active == True).count()
    total_matriculas = db.query(Matricula).count()
    usuarios_activos = db.query(User).filter(User.is_active == True).count()
    estudiantes_activos = db.query(Estudiante).filter(Estudiante.is_active == True).count()
    
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
        "usuarios_inactivos": total_usuarios - usuarios_activos
    }
    
    # Usuarios recientes (últimos 10)
    usuarios_recientes = db.query(User).order_by(User.created_at.desc()).limit(10).all()
    
    # Actividad reciente del sistema
    actividad_sistema = []
    
    # Últimas matrículas
    matriculas_recientes = db.query(Matricula).options(
        joinedload(Matricula.estudiante),
        joinedload(Matricula.curso)
    ).order_by(Matricula.created_at.desc()).limit(5).all()
    
    for matricula in matriculas_recientes:
        actividad_sistema.append({
            "tipo": "matricula",
            "descripcion": f"{matricula.estudiante.first_name} {matricula.estudiante.last_name} se matriculó en {matricula.curso.nombre}",
            "fecha": matricula.created_at,
            "usuario": f"{matricula.estudiante.first_name} {matricula.estudiante.last_name}"
        })
    
    # Últimos estudiantes creados
    estudiantes_nuevos = db.query(Estudiante).order_by(Estudiante.created_at.desc()).limit(3).all()
    for estudiante in estudiantes_nuevos:
        actividad_sistema.append({
            "tipo": "estudiante_creado",
            "descripcion": f"Nuevo estudiante registrado: {estudiante.first_name} {estudiante.last_name}",
            "fecha": estudiante.created_at,
            "usuario": f"{estudiante.first_name} {estudiante.last_name}"
        })
    
    # Ordenar actividad por fecha
    actividad_sistema.sort(key=lambda x: x["fecha"], reverse=True)
    actividad_sistema = actividad_sistema[:10]
    
    # Alertas del sistema
    alertas = []
    
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
@router.get("/usuarios", response_model=List[UserResponse])
def get_usuarios(
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user),
    role: Optional[RoleEnum] = None,
    include_inactive: bool = Query(False)
):
    """Obtener lista de usuarios con filtros"""
    
    query = db.query(User)
    
    if not include_inactive:
        query = query.filter(User.is_active == True)
    if role:
        query = query.filter(User.role == role)
    
    usuarios = query.order_by(User.created_at.desc()).all()
    return usuarios

@router.post("/usuarios", response_model=UserResponse)
def create_usuario(
    usuario_data: UserCreate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Crear un nuevo usuario"""
    
    # Verificar que el DNI no existe
    existing_dni = db.query(User).filter(User.dni == usuario_data.dni).first()
    if existing_dni:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con este DNI"
        )
    
    # Verificar que el email no existe
    existing_email = db.query(User).filter(User.email == usuario_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con este email"
        )
    
    # Hash de la contraseña
    hashed_password = get_password_hash(usuario_data.password)
    
    new_usuario = User(
        **usuario_data.dict(exclude={'password'}),
        hashed_password=hashed_password
    )
    
    db.add(new_usuario)
    db.commit()
    db.refresh(new_usuario)
    
    return new_usuario

@router.put("/usuarios/{usuario_id}", response_model=UserResponse)
def update_usuario(
    usuario_id: int,
    usuario_data: UserUpdate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Actualizar un usuario existente"""
    
    usuario = db.query(User).filter(User.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar duplicados (excluyendo el actual)
    if usuario_data.dni and usuario_data.dni != usuario.dni:
        existing_dni = db.query(User).filter(
            User.dni == usuario_data.dni,
            User.id != usuario_id
        ).first()
        if existing_dni:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro usuario con este DNI"
            )
    
    if usuario_data.email and usuario_data.email != usuario.email:
        existing_email = db.query(User).filter(
            User.email == usuario_data.email,
            User.id != usuario_id
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro usuario con este email"
            )
    
    # Actualizar campos
    for field, value in usuario_data.dict(exclude_unset=True).items():
        if field == 'password' and value:
            setattr(usuario, 'hashed_password', get_password_hash(value))
        elif field != 'password':
            setattr(usuario, field, value)
    
    db.commit()
    db.refresh(usuario)
    
    return usuario

@router.delete("/usuarios/{usuario_id}")
def delete_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Eliminar un usuario (soft delete)"""
    
    usuario = db.query(User).filter(User.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar si es docente y tiene cursos asignados
    if usuario.role == RoleEnum.DOCENTE:
        cursos_asignados = db.query(Curso).filter(
            Curso.docente_id == usuario_id,
            Curso.is_active == True
        ).count()
        
        if cursos_asignados > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar un docente con cursos asignados"
            )
    
    # Soft delete
    usuario.is_active = False
    db.commit()
    
    return {"message": "Usuario eliminado correctamente"}

# ==================== GESTIÓN DE ESTUDIANTES ====================
@router.get("/estudiantes", response_model=List[EstudianteResponse])
def get_estudiantes(
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user),
    carrera_id: Optional[int] = None,
    ciclo_actual: Optional[str] = None,
    include_inactive: bool = Query(False)
):
    """Obtener lista de estudiantes con filtros"""
    
    query = db.query(Estudiante).options(
        joinedload(Estudiante.carrera)
    )
    
    if not include_inactive:
        query = query.filter(Estudiante.is_active == True)
    if carrera_id:
        query = query.filter(Estudiante.carrera_id == carrera_id)
    if ciclo_actual:
        query = query.filter(Estudiante.ciclo_actual == ciclo_actual)
    
    estudiantes = query.all()
    
    # Convertir a formato de respuesta
    estudiantes_response = []
    for estudiante in estudiantes:
        total_matriculas = db.query(Matricula).filter(
            Matricula.estudiante_id == estudiante.id
        ).count()
        
        # Calcular promedio de notas
        promedio_query = db.query(func.avg(Nota.nota)).filter(
            Nota.estudiante_id == estudiante.id
        ).scalar()
        promedio_notas = float(promedio_query) if promedio_query else 0.0
        
        estudiante_data = EstudianteResponse(
            id=estudiante.id,
            dni=estudiante.dni,
            codigo_estudiante=estudiante.codigo_estudiante,
            email=estudiante.email,
            email_institucional=estudiante.email_institucional,
            first_name=estudiante.first_name,
            last_name=estudiante.last_name,
            phone=estudiante.phone,
            ciclo_actual=estudiante.ciclo_actual,
            carrera_id=estudiante.carrera_id,
            is_active=estudiante.is_active,
            created_at=estudiante.created_at,
            updated_at=estudiante.updated_at,
            carrera_nombre=estudiante.carrera.nombre if estudiante.carrera else None,
            total_matriculas=total_matriculas,
            promedio_notas=round(promedio_notas, 2)
        )
        estudiantes_response.append(estudiante_data)
    
    return estudiantes_response

@router.post("/estudiantes", response_model=EstudianteResponse)
def create_estudiante(
    estudiante_data: EstudianteCreate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Crear un nuevo estudiante"""
    
    # Verificar que el DNI no existe
    existing_dni = db.query(Estudiante).filter(Estudiante.dni == estudiante_data.dni).first()
    if existing_dni:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un estudiante con este DNI"
        )
    
    # Verificar que el código de estudiante no existe
    existing_codigo = db.query(Estudiante).filter(Estudiante.codigo_estudiante == estudiante_data.codigo_estudiante).first()
    if existing_codigo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un estudiante con este código"
        )
    
    # Verificar que el email no existe
    existing_email = db.query(Estudiante).filter(Estudiante.email == estudiante_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un estudiante con este email"
        )
    
    # Verificar que la carrera existe
    if estudiante_data.carrera_id:
        carrera = db.query(Carrera).filter(Carrera.id == estudiante_data.carrera_id).first()
        if not carrera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Carrera no encontrada"
            )
    
    # Hash de la contraseña
    hashed_password = get_password_hash(estudiante_data.password)
    
    new_estudiante = Estudiante(
        **estudiante_data.dict(exclude={'password'}),
        hashed_password=hashed_password
    )
    
    db.add(new_estudiante)
    db.commit()
    db.refresh(new_estudiante)
    
    return new_estudiante

@router.put("/estudiantes/{estudiante_id}", response_model=EstudianteResponse)
def update_estudiante(
    estudiante_id: int,
    estudiante_data: EstudianteUpdate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Actualizar un estudiante existente"""
    
    estudiante = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    # Verificar duplicados (excluyendo el actual)
    if estudiante_data.dni and estudiante_data.dni != estudiante.dni:
        existing_dni = db.query(Estudiante).filter(
            Estudiante.dni == estudiante_data.dni,
            Estudiante.id != estudiante_id
        ).first()
        if existing_dni:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro estudiante con este DNI"
            )
    
    if estudiante_data.email and estudiante_data.email != estudiante.email:
        existing_email = db.query(Estudiante).filter(
            Estudiante.email == estudiante_data.email,
            Estudiante.id != estudiante_id
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro estudiante con este email"
            )
    
    # Actualizar campos
    for field, value in estudiante_data.dict(exclude_unset=True).items():
        if field == 'password' and value:
            setattr(estudiante, 'hashed_password', get_password_hash(value))
        elif field != 'password':
            setattr(estudiante, field, value)
    
    db.commit()
    db.refresh(estudiante)
    
    return estudiante

@router.delete("/estudiantes/{estudiante_id}")
def delete_estudiante(
    estudiante_id: int,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Eliminar un estudiante (soft delete)"""
    
    estudiante = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    # Verificar si tiene matrículas
    matriculas = db.query(Matricula).filter(
        Matricula.estudiante_id == estudiante_id
    ).count()
    
    if matriculas > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un estudiante con matrículas registradas"
        )
    
    # Soft delete
    estudiante.is_active = False
    db.commit()
    
    return {"message": "Estudiante eliminado correctamente"}

# ==================== GESTIÓN DE CARRERAS ====================
@router.get("/carreras", response_model=List[CarreraResponse])
def get_carreras(
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user),
    include_inactive: bool = Query(False)
):
    """Obtener lista de carreras"""
    
    query = db.query(Carrera)
    
    if not include_inactive:
        query = query.filter(Carrera.is_active == True)
    
    carreras = query.order_by(Carrera.nombre).all()
    
    # Agregar estadísticas
    carreras_response = []
    for carrera in carreras:
        total_estudiantes = db.query(Estudiante).filter(
            Estudiante.carrera_id == carrera.id,
            Estudiante.is_active == True
        ).count()
        
        total_ciclos = db.query(Ciclo).filter(
            Ciclo.carrera_id == carrera.id,
            Ciclo.is_active == True
        ).count()
        
        carrera_data = CarreraResponse(
            **carrera.__dict__,
            total_estudiantes=total_estudiantes,
            total_ciclos=total_ciclos
        )
        carreras_response.append(carrera_data)
    
    return carreras_response

@router.post("/carreras", response_model=CarreraResponse)
def create_carrera(
    carrera_data: CarreraCreate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Crear una nueva carrera"""
    
    # Verificar que el código no existe
    existing_codigo = db.query(Carrera).filter(Carrera.codigo == carrera_data.codigo).first()
    if existing_codigo:
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
    #current_user: User = Depends(get_admin_user)
):
    """Actualizar una carrera existente"""
    
    carrera = db.query(Carrera).filter(Carrera.id == carrera_id).first()
    if not carrera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrera no encontrada"
        )
    
    # Verificar duplicados de código
    if carrera_data.codigo and carrera_data.codigo != carrera.codigo:
        existing_codigo = db.query(Carrera).filter(
            Carrera.codigo == carrera_data.codigo,
            Carrera.id != carrera_id
        ).first()
        if existing_codigo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otra carrera con este código"
            )
    
    # Actualizar campos
    for field, value in carrera_data.dict(exclude_unset=True).items():
        setattr(carrera, field, value)
    
    db.commit()
    db.refresh(carrera)
    
    return carrera

@router.delete("/carreras/{carrera_id}")
def delete_carrera(
    carrera_id: int,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Eliminar una carrera (soft delete)"""
    
    carrera = db.query(Carrera).filter(Carrera.id == carrera_id).first()
    if not carrera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrera no encontrada"
        )
    
    # Verificar si tiene estudiantes
    total_estudiantes = db.query(Estudiante).filter(
        Estudiante.carrera_id == carrera_id,
        Estudiante.is_active == True
    ).count()
    
    if total_estudiantes > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar una carrera con estudiantes activos"
        )
    
    # Verificar si tiene ciclos activos
    ciclos_activos = db.query(Ciclo).filter(
        Ciclo.carrera_id == carrera_id,
        Ciclo.is_active == True
    ).count()
    
    if ciclos_activos > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar una carrera con ciclos activos"
        )
    
    # Soft delete
    carrera.is_active = False
    db.commit()
    
    return {"message": "Carrera eliminada correctamente"}

# ==================== GESTIÓN DE CICLOS ====================
@router.get("/ciclos", response_model=List[CicloResponse])
def get_ciclos(
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user),
    carrera_id: Optional[int] = None,
    include_inactive: bool = Query(False)
):
    """Obtener lista de ciclos"""
    
    query = db.query(Ciclo).options(joinedload(Ciclo.carrera))
    
    if not include_inactive:
        query = query.filter(Ciclo.is_active == True)
    if carrera_id:
        query = query.filter(Ciclo.carrera_id == carrera_id)
    
    ciclos = query.order_by(Ciclo.numero).all()
    
    # Agregar estadísticas
    ciclos_response = []
    for ciclo in ciclos:
        total_cursos = db.query(Curso).filter(
            Curso.ciclo_id == ciclo.id,
            Curso.is_active == True
        ).count()
        
        total_matriculas = db.query(Matricula).filter(
            Matricula.ciclo_id == ciclo.id
        ).count()
        
        ciclo_data = CicloResponse(
            **ciclo.__dict__,
            carrera_nombre=ciclo.carrera.nombre if ciclo.carrera else None,
            total_cursos=total_cursos,
            total_matriculas=total_matriculas
        )
        ciclos_response.append(ciclo_data)
    
    return ciclos_response

@router.post("/ciclos", response_model=CicloResponse)
def create_ciclo(
    ciclo_data: CicloCreate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Crear un nuevo ciclo"""
    
    # Verificar que la carrera existe
    carrera = db.query(Carrera).filter(Carrera.id == ciclo_data.carrera_id).first()
    if not carrera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrera no encontrada"
        )
    
    # Verificar que no existe un ciclo con el mismo número en la misma carrera
    existing_ciclo = db.query(Ciclo).filter(
        Ciclo.carrera_id == ciclo_data.carrera_id,
        Ciclo.numero == ciclo_data.numero
    ).first()
    
    if existing_ciclo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un ciclo con este número en la carrera seleccionada"
        )
    
    new_ciclo = Ciclo(**ciclo_data.dict())
    db.add(new_ciclo)
    db.commit()
    db.refresh(new_ciclo)
    
    return new_ciclo

@router.put("/ciclos/{ciclo_id}", response_model=CicloResponse)
def update_ciclo(
    ciclo_id: int,
    ciclo_data: CicloUpdate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Actualizar un ciclo existente"""
    
    ciclo = db.query(Ciclo).filter(Ciclo.id == ciclo_id).first()
    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado"
        )
    
    # Verificar duplicados de número en la misma carrera
    if ciclo_data.numero and ciclo_data.numero != ciclo.numero:
        existing_ciclo = db.query(Ciclo).filter(
            Ciclo.carrera_id == ciclo.carrera_id,
            Ciclo.numero == ciclo_data.numero,
            Ciclo.id != ciclo_id
        ).first()
        
        if existing_ciclo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro ciclo con este número en la misma carrera"
            )
    
    # Actualizar campos
    for field, value in ciclo_data.dict(exclude_unset=True).items():
        setattr(ciclo, field, value)
    
    db.commit()
    db.refresh(ciclo)
    
    return ciclo

@router.delete("/ciclos/{ciclo_id}")
def delete_ciclo(
    ciclo_id: int,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Eliminar un ciclo (soft delete)"""
    
    ciclo = db.query(Ciclo).filter(Ciclo.id == ciclo_id).first()
    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado"
        )
    
    # Verificar si tiene cursos activos
    cursos_activos = db.query(Curso).filter(
        Curso.ciclo_id == ciclo_id,
        Curso.is_active == True
    ).count()
    
    if cursos_activos > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un ciclo con cursos activos"
        )
    
    # Verificar si tiene matrículas
    total_matriculas = db.query(Matricula).filter(
        Matricula.ciclo_id == ciclo_id
    ).count()
    
    if total_matriculas > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un ciclo con matrículas registradas"
        )
    
    # Soft delete
    ciclo.is_active = False
    db.commit()
    
    return {"message": "Ciclo eliminado correctamente"}

# ==================== GESTIÓN DE CURSOS ====================
@router.get("/cursos", response_model=List[CursoResponse])
def get_cursos(
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user),
    ciclo_id: Optional[int] = None,
    docente_id: Optional[int] = None,
    include_inactive: bool = Query(False)
):
    """Obtener lista de cursos"""
    
    query = db.query(Curso).options(
        joinedload(Curso.ciclo).joinedload(Ciclo.carrera),
        joinedload(Curso.docente)
    )
    
    if not include_inactive:
        query = query.filter(Curso.is_active == True)
    if ciclo_id:
        query = query.filter(Curso.ciclo_id == ciclo_id)
    if docente_id:
        query = query.filter(Curso.docente_id == docente_id)
    
    cursos = query.order_by(Curso.nombre).all()
    
    # Agregar estadísticas
    cursos_response = []
    for curso in cursos:
        total_matriculas = db.query(Matricula).filter(
            Matricula.curso_id == curso.id
        ).count()
        
        curso_data = CursoResponse(
            **curso.__dict__,
            ciclo_nombre=curso.ciclo.nombre if curso.ciclo else None,
            carrera_nombre=curso.ciclo.carrera.nombre if curso.ciclo and curso.ciclo.carrera else None,
            docente_nombre=f"{curso.docente.first_name} {curso.docente.last_name}" if curso.docente else None,
            total_matriculas=total_matriculas
        )
        cursos_response.append(curso_data)
    
    return cursos_response

@router.post("/cursos", response_model=CursoResponse)
def create_curso(
    curso_data: CursoCreate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Crear un nuevo curso"""
    
    # Verificar que el ciclo existe
    ciclo = db.query(Ciclo).filter(Ciclo.id == curso_data.ciclo_id).first()
    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado"
        )
    
    # Verificar que el código no existe
    existing_codigo = db.query(Curso).filter(Curso.codigo == curso_data.codigo).first()
    if existing_codigo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un curso con este código"
        )
    
    # Verificar que el docente existe (si se proporciona)
    if curso_data.docente_id:
        docente = db.query(User).filter(
            User.id == curso_data.docente_id,
            User.role == RoleEnum.DOCENTE
        ).first()
        if not docente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Docente no encontrado"
            )
    
    new_curso = Curso(**curso_data.dict())
    db.add(new_curso)
    db.commit()
    db.refresh(new_curso)
    
    return new_curso

@router.put("/cursos/{curso_id}", response_model=CursoResponse)
def update_curso(
    curso_id: int,
    curso_data: CursoUpdate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Actualizar un curso existente"""
    
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado"
        )
    
    # Verificar duplicados de código
    if curso_data.codigo and curso_data.codigo != curso.codigo:
        existing_codigo = db.query(Curso).filter(
            Curso.codigo == curso_data.codigo,
            Curso.id != curso_id
        ).first()
        if existing_codigo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro curso con este código"
            )
    
    # Verificar que el docente existe (si se proporciona)
    if curso_data.docente_id and curso_data.docente_id != curso.docente_id:
        docente = db.query(User).filter(
            User.id == curso_data.docente_id,
            User.role == RoleEnum.DOCENTE
        ).first()
        if not docente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Docente no encontrado"
            )
    
    # Actualizar campos
    for field, value in curso_data.dict(exclude_unset=True).items():
        setattr(curso, field, value)
    
    db.commit()
    db.refresh(curso)
    
    return curso

@router.delete("/cursos/{curso_id}")
def delete_curso(
    curso_id: int,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Eliminar un curso (soft delete)"""
    
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado"
        )
    
    # Verificar si tiene matrículas
    total_matriculas = db.query(Matricula).filter(
        Matricula.curso_id == curso_id
    ).count()
    
    if total_matriculas > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un curso con matrículas registradas"
        )
    
    # Soft delete
    curso.is_active = False
    db.commit()
    
    return {"message": "Curso eliminado correctamente"}

# ==================== GESTIÓN DE MATRÍCULAS ====================
@router.get("/matriculas", response_model=List[MatriculaResponse])
def get_matriculas(
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user),
    estudiante_id: Optional[int] = None,
    curso_id: Optional[int] = None,
    ciclo_id: Optional[int] = None
):
    """Obtener lista de matrículas"""
    
    query = db.query(Matricula).options(
        joinedload(Matricula.estudiante),
        joinedload(Matricula.curso),
        joinedload(Matricula.carrera),
        joinedload(Matricula.ciclo)
    )
    
    if estudiante_id:
        query = query.filter(Matricula.estudiante_id == estudiante_id)
    if curso_id:
        query = query.filter(Matricula.curso_id == curso_id)
    if ciclo_id:
        query = query.filter(Matricula.ciclo_id == ciclo_id)
    
    matriculas = query.order_by(Matricula.created_at.desc()).all()
    
    matriculas_response = []
    for matricula in matriculas:
        matricula_data = MatriculaResponse(
            **matricula.__dict__,
            estudiante_nombre=matricula.estudiante.nombre_completo,
            curso_nombre=matricula.curso.nombre,
            carrera_nombre=matricula.carrera.nombre,
            ciclo_nombre=matricula.ciclo.nombre
        )
        matriculas_response.append(matricula_data)
    
    return matriculas_response

@router.post("/matriculas", response_model=MatriculaResponse)
def create_matricula(
    matricula_data: MatriculaCreate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Crear una nueva matrícula"""
    
    # Verificar que el estudiante existe
    estudiante = db.query(Estudiante).filter(Estudiante.id == matricula_data.estudiante_id).first()
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    # Verificar que el curso existe
    curso = db.query(Curso).filter(Curso.id == matricula_data.curso_id).first()
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado"
        )
    
    # Verificar que la carrera existe
    carrera = db.query(Carrera).filter(Carrera.id == matricula_data.carrera_id).first()
    if not carrera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrera no encontrada"
        )
    
    # Verificar que el ciclo existe
    ciclo = db.query(Ciclo).filter(Ciclo.id == matricula_data.ciclo_id).first()
    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado"
        )
    
    # Verificar que no está ya matriculado en el mismo curso y ciclo
    existing_matricula = db.query(Matricula).filter(
        Matricula.estudiante_id == matricula_data.estudiante_id,
        Matricula.curso_id == matricula_data.curso_id,
        Matricula.ciclo_id == matricula_data.ciclo_id
    ).first()
    
    if existing_matricula:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estudiante ya está matriculado en este curso para el ciclo seleccionado"
        )
    
    new_matricula = Matricula(**matricula_data.dict())
    db.add(new_matricula)
    db.commit()
    db.refresh(new_matricula)
    
    return new_matricula

@router.put("/matriculas/{matricula_id}", response_model=MatriculaResponse)
def update_matricula(
    matricula_id: int,
    matricula_data: MatriculaUpdate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Actualizar una matrícula existente"""
    
    matricula = db.query(Matricula).filter(Matricula.id == matricula_id).first()
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Matrícula no encontrada"
        )
    
    # Actualizar campos
    for field, value in matricula_data.dict(exclude_unset=True).items():
        setattr(matricula, field, value)
    
    db.commit()
    db.refresh(matricula)
    
    return matricula

@router.delete("/matriculas/{matricula_id}")
def delete_matricula(
    matricula_id: int,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Eliminar una matrícula"""
    
    matricula = db.query(Matricula).filter(Matricula.id == matricula_id).first()
    if not matricula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Matrícula no encontrada"
        )
    
    # Verificar si tiene notas registradas
    total_notas = db.query(Nota).filter(
        Nota.estudiante_id == matricula.estudiante_id,
        Nota.curso_id == matricula.curso_id
    ).count()
    
    if total_notas > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar una matrícula con notas registradas"
        )
    
    db.delete(matricula)
    db.commit()
    
    return {"message": "Matrícula eliminada correctamente"}

# ==================== GESTIÓN DE NOTAS ====================
@router.get("/notas", response_model=List[NotaResponse])
def get_notas(
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user),
    estudiante_id: Optional[int] = None,
    curso_id: Optional[int] = None
):
    """Obtener lista de notas"""
    
    query = db.query(Nota).options(
        joinedload(Nota.estudiante),
        joinedload(Nota.curso)
    )
    
    if estudiante_id:
        query = query.filter(Nota.estudiante_id == estudiante_id)
    if curso_id:
        query = query.filter(Nota.curso_id == curso_id)
    
    notas = query.order_by(Nota.fecha_evaluacion.desc()).all()
    
    notas_response = []
    for nota in notas:
        nota_data = NotaResponse(
            **nota.__dict__,
            estudiante_nombre=nota.estudiante.nombre_completo,
            curso_nombre=nota.curso.nombre
        )
        notas_response.append(nota_data)
    
    return notas_response

@router.post("/notas", response_model=NotaResponse)
def create_nota(
    nota_data: NotaCreate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Crear una nueva nota"""
    
    # Verificar que el estudiante existe
    estudiante = db.query(Estudiante).filter(Estudiante.id == nota_data.estudiante_id).first()
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    # Verificar que el curso existe
    curso = db.query(Curso).filter(Curso.id == nota_data.curso_id).first()
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado"
        )
    
    # Verificar que la nota está en el rango válido
    if nota_data.nota < 0 or nota_data.nota > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nota debe estar entre 0 y 20"
        )
    
    # Verificar que el peso es válido
    if nota_data.peso <= 0 or nota_data.peso > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El peso debe ser mayor a 0 y menor o igual a 1"
        )
    
    new_nota = Nota(**nota_data.dict())
    db.add(new_nota)
    db.commit()
    db.refresh(new_nota)
    
    return new_nota

@router.put("/notas/{nota_id}", response_model=NotaResponse)
def update_nota(
    nota_id: int,
    nota_data: NotaUpdate,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Actualizar una nota existente y registrar en historial"""
    
    nota = db.query(Nota).filter(Nota.id == nota_id).first()
    if not nota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota no encontrada"
        )
    
    # Verificar que la nueva nota está en el rango válido
    if nota_data.nota and (nota_data.nota < 0 or nota_data.nota > 20):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nota debe estar entre 0 y 20"
        )
    
    # Crear registro en historial antes de actualizar
    if nota_data.nota and nota_data.nota != float(nota.nota):
        historial = HistorialNota(
            nota_id=nota_id,
            nota_anterior=float(nota.nota),
            nota_nueva=nota_data.nota,
            motivo_cambio=nota_data.motivo_cambio or "Modificación por administrador",
          #  usuario_modificacion=f"{current_user.first_name} {current_user.last_name}"
        )
        db.add(historial)
    
    # Actualizar campos
    for field, value in nota_data.dict(exclude_unset=True, exclude={'motivo_cambio'}).items():
        setattr(nota, field, value)
    
    db.commit()
    db.refresh(nota)
    
    return nota

@router.get("/notas/{nota_id}/historial", response_model=List[HistorialNotaResponse])
def get_historial_nota(
    nota_id: int,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Obtener historial de cambios de una nota"""
    
    historial = db.query(HistorialNota).filter(
        HistorialNota.nota_id == nota_id
    ).order_by(HistorialNota.fecha_modificacion.desc()).all()
    
    return historial

# ==================== OPERACIONES MASIVAS ====================
@router.post("/estudiantes/bulk-operation", response_model=ResultadoOperacionMasiva)
def bulk_estudiante_operation(
    operacion: OperacionMasivaEstudiantes,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Realizar operaciones masivas en estudiantes"""
    
    exitosos = 0
    fallidos = 0
    errores = []
    
    for estudiante_id in operacion.estudiante_ids:
        try:
            estudiante = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
            if not estudiante:
                errores.append(f"Estudiante {estudiante_id} no encontrado")
                fallidos += 1
                continue
            
            if operacion.accion == "activate":
                estudiante.is_active = True
            elif operacion.accion == "deactivate":
                # Verificar matrículas antes de desactivar
                matriculas = db.query(Matricula).filter(
                    Matricula.estudiante_id == estudiante_id
                ).count()
                
                if matriculas > 0:
                    errores.append(f"Estudiante {estudiante_id} tiene matrículas registradas")
                    fallidos += 1
                    continue
                
                estudiante.is_active = False
            elif operacion.accion == "delete":
                # Verificar matrículas antes de eliminar
                matriculas = db.query(Matricula).filter(
                    Matricula.estudiante_id == estudiante_id
                ).count()
                
                if matriculas > 0:
                    errores.append(f"Estudiante {estudiante_id} tiene matrículas registradas")
                    fallidos += 1
                    continue
                
                estudiante.is_active = False  # Soft delete
            
            exitosos += 1
            
        except Exception as e:
            errores.append(f"Error con estudiante {estudiante_id}: {str(e)}")
            fallidos += 1
    
    if exitosos > 0:
        db.commit()
    
    return {
        "exitosos": exitosos,
        "fallidos": fallidos,
        "errores": errores,
        "mensaje": f"Operación completada: {exitosos} exitosos, {fallidos} fallidos"
    }

@router.post("/carreras/bulk-operation", response_model=ResultadoOperacionMasiva)
def bulk_carrera_operation(
    operacion: OperacionMasivaCarreras,
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Realizar operaciones masivas en carreras"""
    
    exitosos = 0
    fallidos = 0
    errores = []
    
    for carrera_id in operacion.carrera_ids:
        try:
            carrera = db.query(Carrera).filter(Carrera.id == carrera_id).first()
            if not carrera:
                errores.append(f"Carrera {carrera_id} no encontrada")
                fallidos += 1
                continue
            
            if operacion.accion == "activate":
                carrera.is_active = True
            elif operacion.accion == "deactivate":
                carrera.is_active = False
            elif operacion.accion == "delete":
                # Verificar dependencias antes de eliminar
                estudiantes = db.query(Estudiante).filter(
                    Estudiante.carrera_id == carrera_id,
                    Estudiante.is_active == True
                ).count()
                
                ciclos_activos = db.query(Ciclo).filter(
                    Ciclo.carrera_id == carrera_id,
                    Ciclo.is_active == True
                ).count()
                
                if estudiantes > 0 or ciclos_activos > 0:
                    errores.append(f"Carrera {carrera_id} tiene dependencias activas")
                    fallidos += 1
                    continue
                
                carrera.is_active = False
            
            exitosos += 1
            
        except Exception as e:
            errores.append(f"Error con carrera {carrera_id}: {str(e)}")
            fallidos += 1
    
    if exitosos > 0:
        db.commit()
    
    return {
        "exitosos": exitosos,
        "fallidos": fallidos,
        "errores": errores,
        "mensaje": f"Operación completada: {exitosos} exitosos, {fallidos} fallidos"
    }

# ... (similar para ciclos, cursos, matriculas)

# ==================== ESTADÍSTICAS AVANZADAS ====================
@router.get("/estadisticas/avanzadas")
def get_estadisticas_avanzadas(
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_admin_user)
):
    """Obtener estadísticas avanzadas del sistema"""
    
    # Promedio general de notas por carrera
    promedios_carrera = db.query(
        Carrera.nombre,
        func.avg(Nota.nota).label('promedio')
    ).select_from(Nota)\
     .join(Estudiante, Nota.estudiante_id == Estudiante.id)\
     .join(Carrera, Estudiante.carrera_id == Carrera.id)\
     .group_by(Carrera.id, Carrera.nombre)\
     .all()
    
    # Distribución de estudiantes por ciclo
    estudiantes_por_ciclo = db.query(
        Estudiante.ciclo_actual,
        func.count(Estudiante.id).label('total')
    ).filter(Estudiante.is_active == True)\
     .group_by(Estudiante.ciclo_actual)\
     .all()
    
    # Cursos con mejor y peor rendimiento
    rendimiento_cursos = db.query(
        Curso.nombre,
        func.avg(Nota.nota).label('promedio'),
        func.count(Nota.id).label('total_notas')
    ).select_from(Nota)\
     .join(Curso, Nota.curso_id == Curso.id)\
     .group_by(Curso.id, Curso.nombre)\
     .order_by(func.avg(Nota.nota).desc())\
     .limit(10)\
     .all()
    
    return {
        "promedios_por_carrera": [
            {"carrera": carrera, "promedio": float(promedio)} 
            for carrera, promedio in promedios_carrera
        ],
        "estudiantes_por_ciclo": [
            {"ciclo": ciclo, "total": total} 
            for ciclo, total in estudiantes_por_ciclo if ciclo
        ],
        "top_cursos_mejor_rendimiento": [
            {"curso": curso, "promedio": float(promedio), "total_notas": total_notas}
            for curso, promedio, total_notas in rendimiento_cursos
        ]
    }