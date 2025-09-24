from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

# Schemas para gestión de cursos del docente
class CursoDocenteBase(BaseModel):
    nombre: str
    codigo: str
    creditos: int = Field(..., ge=1, le=10, description="Créditos del curso (1-10)")
    horas_semanales: int = Field(..., ge=1, le=20, description="Horas semanales (1-20)")
    horario: Optional[str] = None
    aula: Optional[str] = None
    max_estudiantes: int = Field(30, ge=5, le=50, description="Máximo de estudiantes (5-50)")

class CursoDocenteCreate(CursoDocenteBase):
    carrera_id: int
    ciclo_id: int

class CursoDocenteUpdate(BaseModel):
    nombre: Optional[str] = None
    horario: Optional[str] = None
    aula: Optional[str] = None
    max_estudiantes: Optional[int] = Field(None, ge=5, le=50)

class CursoDocenteResponse(CursoDocenteBase):
    id: int
    carrera_id: int
    ciclo_id: int
    docente_id: int
    is_active: bool
    created_at: datetime
    
    # Información relacionada
    carrera_nombre: Optional[str] = None
    ciclo_nombre: Optional[str] = None
    total_estudiantes: Optional[int] = None
    
    class Config:
        from_attributes = True

# Schemas para estudiantes en los cursos
class EstudianteEnCurso(BaseModel):
    id: int
    dni: str
    nombres: str
    apellidos: str
    email: str
    fecha_matricula: datetime
    
    class Config:
        from_attributes = True

class EstudianteConNota(EstudianteEnCurso):
    """Estudiante con sus notas en el curso"""
    nota_1: Optional[Decimal] = None
    nota_2: Optional[Decimal] = None
    nota_3: Optional[Decimal] = None
    nota_4: Optional[Decimal] = None
    promedio: Optional[Decimal] = None
    observaciones: Optional[str] = None
    
    class Config:
        from_attributes = True

# Schemas para gestión de notas
class NotaCreate(BaseModel):
    estudiante_id: int
    curso_id: int
    nota_1: Optional[Decimal] = Field(None, ge=0, le=20, description="Nota 1 (0-20)")
    nota_2: Optional[Decimal] = Field(None, ge=0, le=20, description="Nota 2 (0-20)")
    nota_3: Optional[Decimal] = Field(None, ge=0, le=20, description="Nota 3 (0-20)")
    nota_4: Optional[Decimal] = Field(None, ge=0, le=20, description="Nota 4 (0-20)")
    observaciones: Optional[str] = None

class NotaUpdate(BaseModel):
    nota_1: Optional[Decimal] = Field(None, ge=0, le=20, description="Nota 1 (0-20)")
    nota_2: Optional[Decimal] = Field(None, ge=0, le=20, description="Nota 2 (0-20)")
    nota_3: Optional[Decimal] = Field(None, ge=0, le=20, description="Nota 3 (0-20)")
    nota_4: Optional[Decimal] = Field(None, ge=0, le=20, description="Nota 4 (0-20)")
    observaciones: Optional[str] = None

class NotaDocenteResponse(BaseModel):
    id: int
    estudiante_id: int
    curso_id: int
    nota_1: Optional[Decimal] = None
    nota_2: Optional[Decimal] = None
    nota_3: Optional[Decimal] = None
    nota_4: Optional[Decimal] = None
    promedio: Optional[Decimal] = None
    observaciones: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Información del estudiante
    estudiante_dni: str
    estudiante_nombres: str
    estudiante_apellidos: str
    
    class Config:
        from_attributes = True

# Schemas para actualización masiva de notas
class NotaMasiva(BaseModel):
    estudiante_id: int
    nota_1: Optional[Decimal] = Field(None, ge=0, le=20)
    nota_2: Optional[Decimal] = Field(None, ge=0, le=20)
    nota_3: Optional[Decimal] = Field(None, ge=0, le=20)
    nota_4: Optional[Decimal] = Field(None, ge=0, le=20)
    observaciones: Optional[str] = None

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