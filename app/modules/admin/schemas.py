from pydantic import BaseModel, Field, validator, EmailStr
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.shared import RoleEnum

# Schemas para gestión de usuarios
class UserCreate(BaseModel):
    dni: str = Field(..., min_length=8, max_length=8, pattern="^[0-9]{8}$")
    nombres: str = Field(..., min_length=2, max_length=50)
    apellidos: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    role: RoleEnum
    telefono: Optional[str] = Field(None, max_length=15)
    direccion: Optional[str] = Field(None, max_length=200)
    fecha_nacimiento: Optional[datetime] = None
    is_active: bool = True

class UserUpdate(BaseModel):
    nombres: Optional[str] = Field(None, min_length=2, max_length=50)
    apellidos: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    role: Optional[RoleEnum] = None
    telefono: Optional[str] = Field(None, max_length=15)
    direccion: Optional[str] = Field(None, max_length=200)
    fecha_nacimiento: Optional[datetime] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    dni: str
    nombres: str
    apellidos: str
    email: str
    role: RoleEnum
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

# Schemas para gestión de carreras
class CarreraCreate(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=100)
    codigo: str = Field(..., min_length=2, max_length=10)
    descripcion: Optional[str] = None
    duracion_ciclos: int = Field(..., ge=1, le=20)

class CarreraUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    codigo: Optional[str] = Field(None, min_length=2, max_length=10)
    descripcion: Optional[str] = None
    duracion_ciclos: Optional[int] = Field(None, ge=1, le=20)
    is_active: Optional[bool] = None

class CarreraResponse(BaseModel):
    id: int
    nombre: str
    codigo: str
    descripcion: Optional[str] = None
    duracion_ciclos: int
    is_active: bool
    created_at: datetime
    total_cursos: Optional[int] = None
    
    class Config:
        from_attributes = True

# Schemas para gestión de ciclos
class CicloCreate(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=50)
    fecha_inicio: datetime
    fecha_fin: datetime
    fecha_cierre_notas: datetime
    
    @validator('fecha_fin')
    def validate_fecha_fin(cls, v, values):
        if 'fecha_inicio' in values and v <= values['fecha_inicio']:
            raise ValueError('La fecha de fin debe ser posterior a la fecha de inicio')
        return v
    
    @validator('fecha_cierre_notas')
    def validate_fecha_cierre_notas(cls, v, values):
        if 'fecha_fin' in values and v > values['fecha_fin']:
            raise ValueError('La fecha de cierre de notas no puede ser posterior a la fecha de fin')
        return v

class CicloUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=50)
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    fecha_cierre_notas: Optional[datetime] = None
    is_active: Optional[bool] = None

class CicloResponse(BaseModel):
    id: int
    nombre: str
    fecha_inicio: datetime
    fecha_fin: datetime
    fecha_cierre_notas: datetime
    is_active: bool
    created_at: datetime
    total_cursos: Optional[int] = None
    total_matriculas: Optional[int] = None
    
    class Config:
        from_attributes = True

# Schemas para gestión de cursos
class CursoCreate(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=100)
    codigo: str = Field(..., min_length=3, max_length=10)
    creditos: int = Field(..., ge=1, le=10)
    horas_semanales: int = Field(..., ge=1, le=20)
    carrera_id: int
    ciclo_id: int
    docente_id: int
    horario: Optional[str] = None
    aula: Optional[str] = Field(None, max_length=20)
    max_estudiantes: int = Field(30, ge=5, le=100)

class CursoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    codigo: Optional[str] = Field(None, min_length=3, max_length=10)
    creditos: Optional[int] = Field(None, ge=1, le=10)
    horas_semanales: Optional[int] = Field(None, ge=1, le=20)
    carrera_id: Optional[int] = None
    ciclo_id: Optional[int] = None
    docente_id: Optional[int] = None
    horario: Optional[str] = None
    aula: Optional[str] = Field(None, max_length=20)
    max_estudiantes: Optional[int] = Field(None, ge=5, le=100)
    is_active: Optional[bool] = None

class CursoResponse(BaseModel):
    id: int
    nombre: str
    codigo: str
    creditos: int
    horas_semanales: int
    carrera_id: int
    ciclo_id: int
    docente_id: int
    horario: Optional[str] = None
    aula: Optional[str] = None
    max_estudiantes: int
    is_active: bool
    created_at: datetime
    
    # Información relacionada
    carrera_nombre: Optional[str] = None
    ciclo_nombre: Optional[str] = None
    docente_nombre: Optional[str] = None
    total_matriculados: Optional[int] = None
    
    class Config:
        from_attributes = True

# Schemas para gestión de matrículas
class MatriculaCreate(BaseModel):
    estudiante_id: int
    curso_id: int
    ciclo_id: int

class MatriculaUpdate(BaseModel):
    is_active: bool

class MatriculaResponse(BaseModel):
    id: int
    estudiante_id: int
    curso_id: int
    ciclo_id: int
    fecha_matricula: datetime
    is_active: bool
    
    # Información relacionada
    estudiante_nombre: Optional[str] = None
    curso_nombre: Optional[str] = None
    ciclo_nombre: Optional[str] = None
    
    class Config:
        from_attributes = True

# Schemas para dashboard del administrador
class AdminDashboard(BaseModel):
    """Dashboard completo del administrador"""
    estadisticas_generales: dict
    usuarios_recientes: List[UserResponse]
    actividad_sistema: List[dict]
    alertas: List[dict]
    
    class Config:
        from_attributes = True

class EstadisticasGenerales(BaseModel):
    """Estadísticas generales del sistema"""
    total_usuarios: int
    total_estudiantes: int
    total_docentes: int
    total_admins: int
    total_carreras: int
    total_ciclos: int
    total_cursos: int
    total_matriculas: int
    usuarios_activos: int
    usuarios_inactivos: int
    
    class Config:
        from_attributes = True

# Schemas para reportes
class ReporteUsuarios(BaseModel):
    """Reporte detallado de usuarios"""
    usuarios: List[UserResponse]
    estadisticas: EstadisticasGenerales
    filtros_aplicados: dict
    
    class Config:
        from_attributes = True

class ReporteAcademico(BaseModel):
    """Reporte académico general"""
    carreras: List[CarreraResponse]
    ciclos: List[CicloResponse]
    cursos: List[CursoResponse]
    estadisticas: dict
    
    class Config:
        from_attributes = True

# Schemas para configuración del sistema
class ConfiguracionSistema(BaseModel):
    """Configuración general del sistema"""
    nombre_institucion: str = Field(..., min_length=3, max_length=100)
    logo_url: Optional[str] = None
    email_contacto: EmailStr
    telefono_contacto: Optional[str] = None
    direccion: Optional[str] = None
    configuracion_notas: dict
    configuracion_matriculas: dict
    configuracion_notificaciones: dict

# Schemas para filtros y búsquedas
class FiltroUsuarios(BaseModel):
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None

class FiltroCursos(BaseModel):
    carrera_id: Optional[int] = None
    ciclo_id: Optional[int] = None
    docente_id: Optional[int] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None

class FiltroMatriculas(BaseModel):
    estudiante_id: Optional[int] = None
    curso_id: Optional[int] = None
    ciclo_id: Optional[int] = None
    is_active: Optional[bool] = None
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None

# Schemas para operaciones masivas
class OperacionMasivaUsuarios(BaseModel):
    user_ids: List[int]
    accion: str = Field(..., pattern="^(activate|deactivate|delete)$")
    
    @validator('user_ids')
    def validate_user_ids(cls, v):
        if not v:
            raise ValueError('Debe seleccionar al menos un usuario')
        if len(v) > 100:  # Límite de seguridad
            raise ValueError('No se pueden procesar más de 100 usuarios a la vez')
        return v

class ResultadoOperacionMasiva(BaseModel):
    exitosos: int
    fallidos: int
    errores: List[str]
    mensaje: str