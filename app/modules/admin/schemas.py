from pydantic import BaseModel, Field, validator, EmailStr
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

from app.shared import RoleEnum

# ==================== SCHEMAS PARA USUARIOS ====================
class UserCreate(BaseModel):
    dni: str = Field(..., min_length=8, max_length=8, pattern="^[0-9]{8}$")
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    phone: Optional[str] = Field(None, max_length=15)
    role: RoleEnum
    is_active: bool = True

class UserUpdate(BaseModel):
    dni: Optional[str] = Field(None, min_length=8, max_length=8, pattern="^[0-9]{8}$")
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    phone: Optional[str] = Field(None, max_length=15)
    role: Optional[RoleEnum] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    dni: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: RoleEnum
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    last_ip: Optional[str] = None
    last_user_agent: Optional[str] = None
    
    class Config:
        from_attributes = True

# ==================== SCHEMAS PARA ESTUDIANTES ====================
class EstudianteBase(BaseModel):
   
    dni: str = Field(..., min_length=8, max_length=8, pattern="^[0-9]{8}$")
    codigo_estudiante: str = Field(..., min_length=3, max_length=20)
    email: EmailStr
    email_institucional: Optional[EmailStr] = None
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    phone: Optional[str] = Field(None, max_length=15)
    ciclo_actual: Optional[str] = Field(None, max_length=10)
    carrera_id: Optional[int] = None

class EstudianteCreate(EstudianteBase):
    password: str = Field(..., min_length=6, max_length=100)

class EstudianteUpdate(BaseModel):
    dni: Optional[str] = Field(None, min_length=8, max_length=8, pattern="^[0-9]{8}$")
    codigo_estudiante: Optional[str] = Field(None, min_length=3, max_length=20)
    email: Optional[EmailStr] = None
    email_institucional: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    phone: Optional[str] = Field(None, max_length=15)
    ciclo_actual: Optional[str] = Field(None, max_length=10)
    carrera_id: Optional[int] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    is_active: Optional[bool] = None

class EstudianteResponse(EstudianteBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Información relacionada
    first_name: str
    last_name: str
    carrera_nombre: Optional[str] = None
    total_matriculas: int = 0
    promedio_notas: float = 0.0
    
    class Config:
        from_attributes = True

# ==================== SCHEMAS PARA CARRERAS ====================
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
    updated_at: Optional[datetime] = None
    
    # Estadísticas
    total_estudiantes: Optional[int] = 0
    total_ciclos: Optional[int] = 0
    
    class Config:
        from_attributes = True

# ==================== SCHEMAS PARA CICLOS ====================
class CicloCreate(BaseModel):
    numero: int = Field(..., ge=1, le=20)
    carrera_id: int
    nombre: str = Field(..., min_length=3, max_length=50)
    descripcion: Optional[str] = None

class CicloUpdate(BaseModel):
    numero: Optional[int] = Field(None, ge=1, le=20)
    nombre: Optional[str] = Field(None, min_length=3, max_length=50)
    descripcion: Optional[str] = None
    is_active: Optional[bool] = None

class CicloResponse(BaseModel):
    id: int
    numero: int
    carrera_id: int
    nombre: str
    descripcion: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Información relacionada
    carrera_nombre: Optional[str] = None
    total_cursos: Optional[int] = 0
    total_matriculas: Optional[int] = 0
    
    class Config:
        from_attributes = True

# ==================== SCHEMAS PARA CURSOS ====================
class CursoCreate(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=100)
    codigo: str = Field(..., min_length=3, max_length=10)
    descripcion: Optional[str] = None
    creditos: int = Field(..., ge=1, le=10)
    horas_teoricas: int = Field(..., ge=0, le=20)
    horas_practicas: int = Field(..., ge=0, le=20)
    ciclo_id: int
    docente_id: Optional[int] = None

class CursoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    codigo: Optional[str] = Field(None, min_length=3, max_length=10)
    descripcion: Optional[str] = None
    creditos: Optional[int] = Field(None, ge=1, le=10)
    horas_teoricas: Optional[int] = Field(None, ge=0, le=20)
    horas_practicas: Optional[int] = Field(None, ge=0, le=20)
    ciclo_id: Optional[int] = None
    docente_id: Optional[int] = None
    is_active: Optional[bool] = None

class CursoResponse(BaseModel):
    id: int
    nombre: str
    codigo: str
    descripcion: Optional[str] = None
    creditos: int
    horas_teoricas: int
    horas_practicas: int
    ciclo_id: int
    docente_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Información relacionada
    ciclo_nombre: Optional[str] = None
    carrera_nombre: Optional[str] = None
    docente_nombre: Optional[str] = None
    total_matriculas: Optional[int] = 0
    
    class Config:
        from_attributes = True

# ==================== SCHEMAS PARA MATRÍCULAS ====================
class MatriculaCreate(BaseModel):
    estudiante_id: int
    curso_id: int
    carrera_id: int
    ciclo_id: int
    fecha_matricula: date  # ✅ Este campo es OBLIGATORIO en tu modelo
    estado: str = Field("activa", max_length=20)  # ✅ Agregado max_length

class MatriculaUpdate(BaseModel):
    estado: Optional[str] = Field(None, max_length=20)

class MatriculaResponse(BaseModel):
    id: int
    estudiante_id: int
    curso_id: int
    carrera_id: int
    ciclo_id: int
    fecha_matricula: date  # ✅ Corregido: es Date, no DateTime
    estado: str  # ✅ Este campo FALTABA en tu schema anterior
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Información relacionada
    estudiante_nombre: Optional[str] = None
    curso_nombre: Optional[str] = None
    carrera_nombre: Optional[str] = None
    ciclo_nombre: Optional[str] = None
    
    class Config:
        from_attributes = True

# ==================== SCHEMAS PARA NOTAS ====================
class NotaCreate(BaseModel):
    estudiante_id: int
    curso_id: int
    tipo_evaluacion: str = Field(..., min_length=2, max_length=50)
    nota: Decimal = Field(..., ge=0, le=20)
    peso: Decimal = Field(..., gt=0, le=1)
    fecha_evaluacion: date  # ✅ Corregido: es Date, no DateTime
    observaciones: Optional[str] = None

class NotaUpdate(BaseModel):
    tipo_evaluacion: Optional[str] = Field(None, min_length=2, max_length=50)
    nota: Optional[Decimal] = Field(None, ge=0, le=20)
    peso: Optional[Decimal] = Field(None, gt=0, le=1)
    fecha_evaluacion: Optional[date] = None
    observaciones: Optional[str] = None
    motivo_cambio: Optional[str] = None

class NotaResponse(BaseModel):
    id: int
    estudiante_id: int
    curso_id: int
    tipo_evaluacion: str
    nota: Decimal
    peso: Decimal
    fecha_evaluacion: date  # ✅ Corregido: es Date
    observaciones: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Información relacionada
    estudiante_nombre: Optional[str] = None
    curso_nombre: Optional[str] = None
    
    class Config:
        from_attributes = True

# ==================== SCHEMAS PARA HISTORIAL DE NOTAS ====================
class HistorialNotaResponse(BaseModel):
    id: int
    nota_id: int
    nota_anterior: Optional[Decimal] = None
    nota_nueva: Decimal
    motivo_cambio: str
    usuario_modificacion: str
    fecha_modificacion: datetime
    
    class Config:
        from_attributes = True

# ==================== SCHEMAS PARA OPERACIONES MASIVAS ====================
class OperacionMasivaUsuarios(BaseModel):
    user_ids: List[int]
    accion: str = Field(..., pattern="^(activate|deactivate|delete)$")
    
    @validator('user_ids')
    def validate_user_ids(cls, v):
        if not v:
            raise ValueError('Debe seleccionar al menos un usuario')
        if len(v) > 100:
            raise ValueError('No se pueden procesar más de 100 usuarios a la vez')
        return v

class OperacionMasivaEstudiantes(BaseModel):
    estudiante_ids: List[int]
    accion: str = Field(..., pattern="^(activate|deactivate|delete)$")
    
    @validator('estudiante_ids')
    def validate_estudiante_ids(cls, v):
        if not v:
            raise ValueError('Debe seleccionar al menos un estudiante')
        if len(v) > 100:
            raise ValueError('No se pueden procesar más de 100 estudiantes a la vez')
        return v

class OperacionMasivaCarreras(BaseModel):
    carrera_ids: List[int]
    accion: str = Field(..., pattern="^(activate|deactivate|delete)$")
    
    @validator('carrera_ids')
    def validate_carrera_ids(cls, v):
        if not v:
            raise ValueError('Debe seleccionar al menos una carrera')
        if len(v) > 50:
            raise ValueError('No se pueden procesar más de 50 carreras a la vez')
        return v

class OperacionMasivaCiclos(BaseModel):
    ciclo_ids: List[int]
    accion: str = Field(..., pattern="^(activate|deactivate|delete)$")
    
    @validator('ciclo_ids')
    def validate_ciclo_ids(cls, v):
        if not v:
            raise ValueError('Debe seleccionar al menos un ciclo')
        if len(v) > 50:
            raise ValueError('No se pueden procesar más de 50 ciclos a la vez')
        return v

class OperacionMasivaCursos(BaseModel):
    curso_ids: List[int]
    accion: str = Field(..., pattern="^(activate|deactivate|delete)$")
    
    @validator('curso_ids')
    def validate_curso_ids(cls, v):
        if not v:
            raise ValueError('Debe seleccionar al menos un curso')
        if len(v) > 50:
            raise ValueError('No se pueden procesar más de 50 cursos a la vez')
        return v

class OperacionMasivaMatriculas(BaseModel):
    matricula_ids: List[int]
    accion: str = Field(..., pattern="^(activate|deactivate|delete)$")
    
    @validator('matricula_ids')
    def validate_matricula_ids(cls, v):
        if not v:
            raise ValueError('Debe seleccionar al menos una matrícula')
        if len(v) > 100:
            raise ValueError('No se pueden procesar más de 100 matrículas a la vez')
        return v

class ResultadoOperacionMasiva(BaseModel):
    exitosos: int
    fallidos: int
    errores: List[str]
    mensaje: str

# ==================== SCHEMAS PARA FILTROS ====================
class FiltroUsuarios(BaseModel):
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None

class FiltroEstudiantes(BaseModel):
    carrera_id: Optional[int] = None
    ciclo_actual: Optional[str] = None
    include_inactive: Optional[bool] = False
    search: Optional[str] = None

class FiltroCarreras(BaseModel):
    include_inactive: Optional[bool] = False
    search: Optional[str] = None

class FiltroCiclos(BaseModel):
    carrera_id: Optional[int] = None
    include_inactive: Optional[bool] = False
    search: Optional[str] = None

class FiltroCursos(BaseModel):
    ciclo_id: Optional[int] = None
    docente_id: Optional[int] = None
    include_inactive: Optional[bool] = False
    search: Optional[str] = None

class FiltroMatriculas(BaseModel):
    estudiante_id: Optional[int] = None
    curso_id: Optional[int] = None
    ciclo_id: Optional[int] = None
    search: Optional[str] = None

class FiltroNotas(BaseModel):
    estudiante_id: Optional[int] = None
    curso_id: Optional[int] = None
    search: Optional[str] = None

# ==================== SCHEMAS PARA LISTAS PAGINADAS ====================
class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class EstudianteListResponse(BaseModel):
    estudiantes: List[EstudianteResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class CarreraListResponse(BaseModel):
    carreras: List[CarreraResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class CicloListResponse(BaseModel):
    ciclos: List[CicloResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class CursoListResponse(BaseModel):
    cursos: List[CursoResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class MatriculaListResponse(BaseModel):
    matriculas: List[MatriculaResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class NotaListResponse(BaseModel):
    notas: List[NotaResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

# ==================== SCHEMAS PARA ESTADÍSTICAS AVANZADAS ====================
class EstadisticaCarrera(BaseModel):
    carrera: str
    promedio: float
    total_estudiantes: int

class EstadisticaCiclo(BaseModel):
    ciclo: str
    total_estudiantes: int

class EstadisticaCurso(BaseModel):
    curso: str
    promedio: float
    total_notas: int

class EstadisticasAvanzadasResponse(BaseModel):
    promedios_por_carrera: List[EstadisticaCarrera]
    estudiantes_por_ciclo: List[EstadisticaCiclo]
    top_cursos_mejor_rendimiento: List[EstadisticaCurso]

# ==================== SCHEMAS PARA DASHBOARD (NO MODIFICADOS) ====================
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

# ==================== SCHEMAS PARA CONFIGURACIÓN ====================
class ConfiguracionSistema(BaseModel):
    nombre_institucion: str = Field(..., min_length=3, max_length=100)
    email_contacto: EmailStr
    telefono_contacto: Optional[str] = None
    direccion: Optional[str] = None

# ==================== SCHEMAS PARA REPORTES ====================
class ReporteUsuarios(BaseModel):
    usuarios: List[UserResponse]
    estadisticas: dict
    filtros_aplicados: dict

class ReporteAcademico(BaseModel):
    carreras: List[CarreraResponse]
    ciclos: List[CicloResponse]
    cursos: List[CursoResponse]
    estadisticas: dict