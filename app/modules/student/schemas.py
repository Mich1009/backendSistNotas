from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

# Schemas para Carrera
class CarreraBase(BaseModel):
    nombre: str
    codigo: str
    descripcion: Optional[str] = None
    duracion_ciclos: int

class CarreraResponse(CarreraBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schemas para Ciclo
class CicloBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    fecha_inicio: datetime
    fecha_fin: datetime

class CicloResponse(CicloBase):
    id: int
    carrera_id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schemas para Curso
class CursoBase(BaseModel):
    nombre: str
    codigo: str
    creditos: int
    horas_semanales: int
    horario: Optional[str] = None
    aula: Optional[str] = None
    max_estudiantes: int = 30

class CursoResponse(CursoBase):
    id: int
    carrera_id: int
    ciclo_id: int
    docente_id: int
    is_active: bool
    created_at: datetime
    
    # Información relacionada
    carrera: Optional[CarreraResponse] = None
    ciclo: Optional[CicloResponse] = None
    
    class Config:
        from_attributes = True

class CursoEstudianteResponse(BaseModel):
    """Información del curso desde la perspectiva del estudiante"""
    id: int
    nombre: str
    codigo: str
    creditos: int
    horas_semanales: int
    docente_nombre: str
    ciclo_nombre: str
    
    class Config:
        from_attributes = True

# Schemas para Matrícula
class MatriculaBase(BaseModel):
    curso_id: int
    ciclo_id: int

class MatriculaCreate(MatriculaBase):
    pass

class MatriculaResponse(MatriculaBase):
    id: int
    estudiante_id: int
    fecha_matricula: datetime
    is_active: bool
    
    # Información relacionada
    curso: Optional[CursoResponse] = None
    ciclo: Optional[CicloResponse] = None
    
    class Config:
        from_attributes = True

# Schemas para Notas
class NotaEstudianteResponse(BaseModel):
    """Vista de notas desde la perspectiva del estudiante"""
    id: int
    curso_nombre: str
    curso_codigo: str
    docente_nombre: str
    tipo_evaluacion: str
    valor_nota: Decimal
    peso: Decimal
    fecha_evaluacion: str
    observaciones: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class PromedioFinalEstudianteResponse(BaseModel):
    """Promedio final del estudiante en un curso"""
    curso_id: int
    curso_nombre: str
    curso_codigo: str
    promedio_final: Decimal
    estado: str  # APROBADO, DESAPROBADO, SIN_NOTAS
    detalle: dict
    
    class Config:
        from_attributes = True

class NotasPorTipoResponse(BaseModel):
    """Notas agrupadas por tipo de evaluación"""
    curso_id: int
    curso_nombre: str
    curso_codigo: str
    notas_semanales: List[NotaEstudianteResponse]
    notas_practicas: List[NotaEstudianteResponse]
    notas_parciales: List[NotaEstudianteResponse]
    promedio_final: Optional[Decimal] = None
    estado: Optional[str] = None
    
    class Config:
        from_attributes = True

# Schemas para Dashboard del Estudiante
class EstudianteDashboard(BaseModel):
    """Información completa del dashboard del estudiante"""
    estudiante_info: dict
    cursos_actuales: List[CursoEstudianteResponse]
    notas_recientes: List[NotaEstudianteResponse]
    estadisticas: dict
    
    class Config:
        from_attributes = True

class EstadisticasEstudiante(BaseModel):
    """Estadísticas del rendimiento del estudiante"""
    total_cursos: int
    promedio_general: Optional[Decimal] = None
    cursos_aprobados: int
    cursos_desaprobados: int
    creditos_completados: int
    
    class Config:
        from_attributes = True

# Schemas para solicitudes de matrícula
class SolicitudMatricula(BaseModel):
    cursos_ids: List[int] = Field(..., description="Lista de IDs de cursos para matricularse")
    ciclo_id: int = Field(..., description="ID del ciclo académico")
    
    @validator('cursos_ids')
    def validate_cursos_ids(cls, v):
        if not v:
            raise ValueError('Debe seleccionar al menos un curso')
        if len(v) > 8:  # Límite máximo de cursos por ciclo
            raise ValueError('No puede matricularse en más de 8 cursos por ciclo')
        return v