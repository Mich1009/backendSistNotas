from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal

# Schemas específicos para el Dashboard
class EstudianteInfo(BaseModel):
    first_name: str
    last_name: str
    email: str
    dni:str
    codigo_estudiante: Optional[str] = None

class CursoDashboard(BaseModel):
    id: int
    nombre: str
    codigo: str
    docente_nombre: str
    ciclo_nombre: str
    creditos: Optional[int] = 3

class NotaDashboard(BaseModel):
    """Esquema simplificado para el dashboard - USANDO CAMPOS REALES"""
    id: int
    curso_nombre: str
    curso_codigo: str
    docente_nombre: str
    ciclo_nombre: str
    
    # SOLO CAMPOS QUE EXISTEN EN EL MODELO
    evaluacion1: Optional[float] = None
    evaluacion2: Optional[float] = None
    evaluacion3: Optional[float] = None
    evaluacion4: Optional[float] = None
    evaluacion5: Optional[float] = None
    evaluacion6: Optional[float] = None
    evaluacion7: Optional[float] = None
    evaluacion8: Optional[float] = None
    
    practica1: Optional[float] = None
    practica2: Optional[float] = None
    practica3: Optional[float] = None
    practica4: Optional[float] = None
    
    parcial1: Optional[float] = None
    parcial2: Optional[float] = None
    
    promedio_final: Optional[float] = None
    estado: Optional[str] = None
    
    fecha_actualizacion: str

class EstadisticasDashboard(BaseModel):
    total_cursos: int
    promedio_general: float
    cursos_aprobados: int
    cursos_desaprobados: int
    creditos_completados: int


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
    docente_nombre: str
    ciclo_nombre: str
    
    class Config:
        from_attributes = True

# Schemas para Matrícula
class MatriculaBase(BaseModel):
    ciclo_id: int

class MatriculaCreate(MatriculaBase):
    pass

class MatriculaResponse(MatriculaBase):
    id: int
    estudiante_id: int
    fecha_matricula: datetime
    is_active: bool
    
    # Información relacionada
    ciclo: Optional[CicloResponse] = None
    
    class Config:
        from_attributes = True


# para el dashboard
class CursoConNotasResponse(BaseModel):
    """Curso con todas sus notas - SISTEMA NUEVO"""
    curso: 'CursoEstudianteResponse'
    notas: List['NotaEstudianteResponse']
    promedio_final: Optional[Decimal] = None
    estado: Optional[str] = None
    
    class Config:
        from_attributes = True

class PromedioFinalEstudianteResponse(BaseModel):
    """Promedio final del estudiante en un curso"""
    curso_id: int
    curso_nombre: str
    promedio_final: Decimal
    estado: str  # APROBADO, DESAPROBADO, SIN_NOTAS
    detalle: dict
    
    class Config:
        from_attributes = True

# Schemas para Notas - SISTEMA NUEVO
class NotaEstudianteResponse(BaseModel):
    """Vista de notas desde la perspectiva del estudiante - SISTEMA NUEVO"""
    id: int
    curso_id: int
    curso_nombre: str
    docente_nombre: str
    ciclo_nombre: Optional[str] = None
    ciclo_año: Optional[int] = None
    
    # Promedios por tipo de evaluación
    promedio_evaluaciones: Optional[float] = None
    promedio_practicas: Optional[float] = None
    promedio_parciales: Optional[float] = None
    
    # Promedio final ponderado
    promedio_final: Optional[float] = None
    estado: Optional[str] = None
    
    # Notas individuales
    evaluacion1: Optional[float] = None
    evaluacion2: Optional[float] = None
    evaluacion3: Optional[float] = None
    evaluacion4: Optional[float] = None
    evaluacion5: Optional[float] = None
    evaluacion6: Optional[float] = None
    evaluacion7: Optional[float] = None
    evaluacion8: Optional[float] = None
    
    practica1: Optional[float] = None
    practica2: Optional[float] = None
    practica3: Optional[float] = None
    practica4: Optional[float] = None
    
    parcial1: Optional[float] = None
    parcial2: Optional[float] = None
    
    fecha_registro: Optional[date] = None
    observaciones: Optional[str] = None
    
    class Config:
        from_attributes = True

class NotaDetalladaResponse(BaseModel):
    """Nota con todos los campos detallados"""
    id: int
    curso_id: int
    curso_nombre: str
    docente_nombre: str
    
    # Promedios por tipo de evaluación
    promedio_evaluaciones: Optional[float] = None
    promedio_practicas: Optional[float] = None
    promedio_parciales: Optional[float] = None
    
    # Promedio final ponderado
    promedio_final: Optional[float] = None
    estado: Optional[str] = None
    
    # Notas individuales detalladas
    evaluaciones: List[Dict[str, Any]] = []  # Lista de evaluaciones semanales
    practicas: List[Dict[str, Any]] = []     # Lista de prácticas
    parciales: List[Dict[str, Any]] = []     # Lista de parciales
    
    fecha_registro: Optional[datetime] = None
    observaciones: Optional[str] = None
    
    class Config:
        from_attributes = True
      
class NotasPorTipoResponse(BaseModel):
    """Notas agrupadas por tipo de evaluación - SISTEMA NUEVO"""
    curso_id: int
    curso_nombre: str
    
    # Notas agrupadas por tipo
    evaluaciones_semanales: List[NotaEstudianteResponse] = Field(default_factory=list)
    evaluaciones_practicas: List[NotaEstudianteResponse] = Field(default_factory=list)
    evaluaciones_parciales: List[NotaEstudianteResponse] = Field(default_factory=list)
    
    promedio_final: Optional[Decimal] = None
    estado: Optional[str] = None
    
    class Config:
        from_attributes = True

class EstudianteDashboard(BaseModel):
    """Información completa del dashboard del estudiante"""
    estudiante_info: EstudianteInfo
    cursos_actuales: List[CursoDashboard]
    notas_recientes: List[NotaDashboard]
    estadisticas: EstadisticasDashboard
    
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

# Forward references
CursoConNotasResponse.update_forward_refs()

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