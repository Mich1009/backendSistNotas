from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

# Schemas para perfil de docente
class DocenteProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    phone: Optional[str] = Field(None, min_length=9, max_length=15)
    especialidad: Optional[str] = Field(None, min_length=3, max_length=100)
    grado_academico: Optional[str] = Field(None, min_length=3, max_length=50)

class PasswordUpdate(BaseModel):
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v

# Schemas para gestión de cursos del docente
class CursoDocenteBase(BaseModel):
    nombre: str
    horario: Optional[str] = None
    aula: Optional[str] = None
    max_estudiantes: int = Field(30, ge=5, le=50, description="Máximo de estudiantes (5-50)")

class CursoDocenteCreate(CursoDocenteBase):
    carrera_id: int
    ciclo_id: int

class CursoDocenteUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)

class CursoDocenteResponse(BaseModel):
    id: int
    nombre: str
    ciclo_id: int
    docente_id: int
    is_active: bool
    created_at: datetime
    ciclo_nombre: Optional[str] = None
    ciclo_año: Optional[int] = None
    total_estudiantes: Optional[int] = None
    
    class Config:
        from_attributes = True

# Schemas para estudiantes en los cursos
class EstudianteEnCurso(BaseModel):
    id: int
    dni: str
    first_name: str
    last_name: str
    email: str
    fecha_matricula: datetime
    
    class Config:
        from_attributes = True

class NotaResponse(BaseModel):
    id: int
    estudiante_id: int
    estudiante_nombre: str
    tipo_evaluacion: str
    nota: float
    peso: float
    fecha_evaluacion: str
    observaciones: str | None

    class Config:
        from_attributes = True

class EstudianteConNota(EstudianteEnCurso):
    """Estudiante con sus notas en el curso"""
    notas: Optional[List[dict]] = None  # Lista de todas las notas del estudiante
    
    class Config:
        from_attributes = True

# Schemas para gestión de notas
class NotaCreate(BaseModel):
    estudiante_id: int
    curso_id: int
    tipo_evaluacion: str = Field(..., description="Tipo de evaluación: SEMANAL, PRACTICA, PARCIAL")
    valor_nota: Decimal = Field(..., ge=0, le=20, description="Valor de la nota (0-20)")
    fecha_evaluacion: str = Field(..., description="Fecha de evaluación (YYYY-MM-DD)")
    observaciones: Optional[str] = None
    
    @validator('tipo_evaluacion')
    def validate_tipo_evaluacion(cls, v):
        tipos_validos = ['SEMANAL', 'PRACTICA', 'PARCIAL']
        if v not in tipos_validos:
            raise ValueError(f'Tipo de evaluación debe ser uno de: {tipos_validos}')
        return v

class NotaUpdate(BaseModel):
    valor_nota: Optional[Decimal] = Field(None, ge=0, le=20, description="Valor de la nota (0-20)")
    fecha_evaluacion: Optional[str] = Field(None, description="Fecha de evaluación (YYYY-MM-DD)")
    observaciones: Optional[str] = None

class NotaDocenteResponse(BaseModel):
    id: int
    estudiante_id: int
    curso_id: int
    tipo_evaluacion: str
    valor_nota: Decimal
    peso: Decimal
    fecha_evaluacion: str
    observaciones: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Información del estudiante
    estudiante_nombre: str
    curso_nombre: str
    
    class Config:
        from_attributes = True

# Schemas para actualización masiva de notas
class NotaMasiva(BaseModel):
    estudiante_id: int
    tipo_evaluacion: str = Field(..., description="Tipo de evaluación: SEMANAL, PRACTICA, PARCIAL")
    valor_nota: Decimal = Field(..., ge=0, le=20, description="Valor de la nota (0-20)")
    fecha_evaluacion: str = Field(..., description="Fecha de evaluación (YYYY-MM-DD)")
    observaciones: Optional[str] = None
    
    @validator('tipo_evaluacion')
    def validate_tipo_evaluacion(cls, v):
        tipos_validos = ['SEMANAL', 'PRACTICA', 'PARCIAL']
        if v not in tipos_validos:
            raise ValueError(f'Tipo de evaluación debe ser uno de: {tipos_validos}')
        return v

class ActualizacionMasivaNotas(BaseModel):
    curso_id: int
    notas: List[NotaMasiva]
    
    @validator('notas')
    def validate_notas(cls, v):
        if not v:
            raise ValueError('Debe proporcionar al menos una nota')
        if len(v) > 50:  # Límite de seguridad
            raise ValueError('No se pueden actualizar más de 50 notas a la vez')
        return v

# Schemas para cálculos de promedios
class PromedioFinalResponse(BaseModel):
    estudiante_id: int
    curso_id: int
    promedio_final: Decimal
    estado: str  # APROBADO, DESAPROBADO, SIN_NOTAS
    detalle: dict
    
    class Config:
        from_attributes = True

class EstructuraNotasResponse(BaseModel):
    estudiante_id: int
    curso_id: int
    notas_semanales: dict
    notas_practicas: dict
    notas_parciales: dict
    estructura_completa: bool
    
    class Config:
        from_attributes = True

# Schemas para dashboard del docente
class DocenteDashboard(BaseModel):
    """Dashboard completo del docente"""
    docente_info: dict
    cursos_actuales: List[CursoDocenteResponse]
    estadisticas_generales: dict
    actividad_reciente: List[dict]
    
    class Config:
        from_attributes = True

class EstadisticasDocente(BaseModel):
    """Estadísticas del docente"""
    total_cursos: int
    total_estudiantes: int
    promedio_general_cursos: Optional[Decimal] = None
    estudiantes_aprobados: int
    estudiantes_desaprobados: int
    cursos_por_ciclo: dict
    
    class Config:
        from_attributes = True

# Schemas para reportes
class ReporteCurso(BaseModel):
    """Reporte detallado de un curso"""
    curso_info: CursoDocenteResponse
    estudiantes: List[EstudianteConNota]
    estadisticas: dict
    
    class Config:
        from_attributes = True

class EstadisticasCurso(BaseModel):
    """Estadísticas específicas de un curso"""
    total_estudiantes: int
    promedio_curso: Optional[Decimal] = None
    estudiantes_aprobados: int
    estudiantes_desaprobados: int
    estudiantes_sin_notas: int
    distribucion_notas: dict
    
    class Config:
        from_attributes = True

# Schemas para exportación
class ExportacionNotas(BaseModel):
    """Datos para exportar notas"""
    curso_id: int
    formato: str = Field("excel", pattern="^(excel|csv|pdf)$")
    incluir_estadisticas: bool = True
    
class ConfiguracionCurso(BaseModel):
    """Configuración específica del curso"""
    permitir_modificacion_notas: bool = True
    fecha_limite_notas: Optional[datetime] = None
    notificaciones_activas: bool = True
    plantilla_observaciones: Optional[str] = None