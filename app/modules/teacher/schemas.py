from pydantic import BaseModel, Field, validator, ConfigDict
from typing import List, Optional,Dict, Any
from datetime import datetime, date
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
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    estudiante_id: int
    curso_id: int
    tipo_evaluacion: str
    
    # Todas las evaluaciones
    evaluacion1: Optional[Decimal] = None
    evaluacion2: Optional[Decimal] = None
    evaluacion3: Optional[Decimal] = None
    evaluacion4: Optional[Decimal] = None
    evaluacion5: Optional[Decimal] = None
    evaluacion6: Optional[Decimal] = None
    evaluacion7: Optional[Decimal] = None
    evaluacion8: Optional[Decimal] = None
    
    practica1: Optional[Decimal] = None
    practica2: Optional[Decimal] = None
    practica3: Optional[Decimal] = None
    practica4: Optional[Decimal] = None
    
    parcial1: Optional[Decimal] = None
    parcial2: Optional[Decimal] = None
    
    promedio_final: Optional[Decimal] = None
    estado: Optional[str] = None
    
    peso: Decimal
    fecha_evaluacion: date
    observaciones: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Información relacionada
    estudiante_nombre: Optional[str] = None
    curso_nombre: Optional[str] = None


class EstudianteConNota(EstudianteEnCurso):
    """Estudiante con sus notas en el curso"""
    notas: Optional[List[dict]] = None  # Lista de todas las notas del estudiante
    
    class Config:
        from_attributes = True

# Schemas para gestión de notas
class NotaBase(BaseModel):
    estudiante_id: int
    curso_id: int
    tipo_evaluacion: str = Field(..., description="Tipo de evaluación: EVALUACION, PRACTICA, PARCIAL")
    
    # Campos de evaluaciones (8 evaluaciones posibles)
    evaluacion1: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion2: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion3: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion4: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion5: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion6: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion7: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion8: Optional[Decimal] = Field(None, ge=0, le=20)
    
    # Campos de prácticas (4 prácticas posibles)
    practica1: Optional[Decimal] = Field(None, ge=0, le=20)
    practica2: Optional[Decimal] = Field(None, ge=0, le=20)
    practica3: Optional[Decimal] = Field(None, ge=0, le=20)
    practica4: Optional[Decimal] = Field(None, ge=0, le=20)
    
    # Campos de parciales (2 parciales)
    parcial1: Optional[Decimal] = Field(None, ge=0, le=20)
    parcial2: Optional[Decimal] = Field(None, ge=0, le=20)
    
    # Resultados finales
    promedio_final: Optional[Decimal] = Field(None, ge=0, le=20)
    estado: Optional[str] = Field(None, description="APROBADO, DESAPROBADO")
    
    peso: Decimal = Field(1.0, ge=0, le=1)
    fecha_evaluacion: date
    observaciones: Optional[str] = None

    @validator('tipo_evaluacion')
    def validar_tipo(cls, v):
        tipos_validos = ['EVALUACION', 'PRACTICA', 'PARCIAL', 'FINAL']
        if v not in tipos_validos:
            raise ValueError(f'Tipo de evaluación debe ser uno de: {tipos_validos}')
        return v

class NotaCreate(NotaBase):
    pass

class NotaUpdate(BaseModel):
    # Campos actualizables individualmente
    evaluacion1: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion2: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion3: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion4: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion5: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion6: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion7: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion8: Optional[Decimal] = Field(None, ge=0, le=20)
    
    practica1: Optional[Decimal] = Field(None, ge=0, le=20)
    practica2: Optional[Decimal] = Field(None, ge=0, le=20)
    practica3: Optional[Decimal] = Field(None, ge=0, le=20)
    practica4: Optional[Decimal] = Field(None, ge=0, le=20)
    
    parcial1: Optional[Decimal] = Field(None, ge=0, le=20)
    parcial2: Optional[Decimal] = Field(None, ge=0, le=20)
    
    promedio_final: Optional[Decimal] = Field(None, ge=0, le=20)
    estado: Optional[str] = Field(None, description="APROBADO, DESAPROBADO")
    
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

class NotaMasivaCreate(BaseModel):
    estudiante_id: int
    curso_id: int  # ← MANTÉN curso_id aquí
    tipo_evaluacion: str = Field("EVALUACION", description="Tipo de evaluación: EVALUACION, PRACTICA, PARCIAL")
    fecha_evaluacion: date
    observaciones: Optional[str] = None
    peso: Decimal = Field(1.0, ge=0, le=1)  # ← MANTÉN peso
    
    # Campos de evaluaciones
    evaluacion1: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion2: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion3: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion4: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion5: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion6: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion7: Optional[Decimal] = Field(None, ge=0, le=20)
    evaluacion8: Optional[Decimal] = Field(None, ge=0, le=20)
    
    practica1: Optional[Decimal] = Field(None, ge=0, le=20)
    practica2: Optional[Decimal] = Field(None, ge=0, le=20)
    practica3: Optional[Decimal] = Field(None, ge=0, le=20)
    practica4: Optional[Decimal] = Field(None, ge=0, le=20)
    
    parcial1: Optional[Decimal] = Field(None, ge=0, le=20)
    parcial2: Optional[Decimal] = Field(None, ge=0, le=20)

    @validator('tipo_evaluacion')
    def validar_tipo(cls, v):
        tipos_validos = ['EVALUACION', 'PRACTICA', 'PARCIAL']
        if v not in tipos_validos:
            raise ValueError(f'Tipo de evaluación debe ser uno de: {tipos_validos}')
        return v

# 🔥 CAMBIA ESTE SCHEMA - elimina el curso_id del nivel superior
class ActualizacionMasivaNotas(BaseModel):
    notas: List[NotaMasivaCreate]
    
    @validator('notas')
    def validar_notas(cls, v):
        if not v:
            raise ValueError('Debe proporcionar al menos una nota')
        if len(v) > 50:
            raise ValueError('No se pueden procesar más de 50 notas a la vez')
        return v
    
# Schema para cálculo de promedios
class CalculoPromedioRequest(BaseModel):
    curso_id: int
    estudiante_id: int
    configuracion: Optional[Dict[str, Any]] = Field(default_factory=dict)

class PromedioFinalResponse(BaseModel):
    estudiante_id: int
    curso_id: int
    promedio_final: Decimal
    estado: str  # APROBADO, DESAPROBADO, EN_PROCESO
    detalle_calculo: Dict[str, Any]
    notas_completas: bool
    
    model_config = ConfigDict(from_attributes=True)

# Schemas para dashboard del docente
# Schema para estructura de notas del estudiante
class EstructuraNotasResponse(BaseModel):
    estudiante_id: int
    curso_id: int
    evaluaciones: Dict[str, Optional[Decimal]]
    practicas: Dict[str, Optional[Decimal]]
    parciales: Dict[str, Optional[Decimal]]
    promedio_parcial: Optional[Decimal]
    promedio_final: Optional[Decimal]
    estado: str
    completitud: float  # Porcentaje de completitud (0-100)
    
    model_config = ConfigDict(from_attributes=True)

# Schema para reporte de curso completo
class ReporteCursoCompleto(BaseModel):
    curso_info: Dict[str, Any]
    estudiantes: List[Dict[str, Any]]
    estadisticas: Dict[str, Any]
    distribucion_notas: Dict[str, int]
    promedios_por_tipo: Dict[str, Decimal]
    
    model_config = ConfigDict(from_attributes=True)

# Schema para configuración de cálculo de notas
class ConfiguracionCalculoNotas(BaseModel):
    curso_id: int
    peso_evaluaciones: Decimal = Field(0.4, ge=0, le=1)
    peso_practicas: Decimal = Field(0.3, ge=0, le=1)
    peso_parciales: Decimal = Field(0.3, ge=0, le=1)
    nota_minima_aprobatoria: Decimal = Field(11, ge=0, le=20)
    incluir_mejores_evaluaciones: Optional[int] = Field(None, ge=1, le=8)
    formula_personalizada: Optional[str] = None

# Schema para histórico de cambios
class HistorialNotaResponse(BaseModel):
    id: int
    nota_id: int
    estudiante_id: int
    curso_id: int
    nota_anterior: Optional[Decimal]
    nota_nueva: Decimal
    motivo_cambio: str
    usuario_modificacion: str
    fecha_modificacion: datetime
    cambios_detallados: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)

# Schemas para dashboard del docente - MEJORADOS
class EstadisticasCursoDetalladas(BaseModel):
    total_estudiantes: int
    estudiantes_con_notas: int
    promedio_general: Optional[Decimal]
    nota_maxima: Optional[Decimal]
    nota_minima: Optional[Decimal]
    estudiantes_aprobados: int
    estudiantes_desaprobados: int
    estudiantes_sin_notas: int
    tasa_aprobacion: Decimal
    distribucion_rangos: Dict[str, int]
    completitud_notas: Decimal
    
    model_config = ConfigDict(from_attributes=True)

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

# Utilidades para cálculos
class NotasCalculo(BaseModel):
    """Estructura para cálculos de promedios"""
    evaluaciones: List[Decimal]
    practicas: List[Decimal]
    parciales: List[Decimal]
    
    def calcular_promedio_evaluaciones(self, incluir_mejores: Optional[int] = None) -> Optional[Decimal]:
        if not self.evaluaciones:
            return None
        
        evaluaciones_validas = [n for n in self.evaluaciones if n is not None]
        if not evaluaciones_validas:
            return None
            
        if incluir_mejores and len(evaluaciones_validas) > incluir_mejores:
            evaluaciones_validas.sort(reverse=True)
            evaluaciones_validas = evaluaciones_validas[:incluir_mejores]
            
        return sum(evaluaciones_validas) / len(evaluaciones_validas)

# Response para búsqueda y filtros
class NotasFilter(BaseModel):
    curso_id: Optional[int] = None
    estudiante_id: Optional[int] = None
    tipo_evaluacion: Optional[str] = None
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    estado: Optional[str] = None
    solo_con_notas: bool = False

class NotasPaginationResponse(BaseModel):
    items: List[NotaResponse]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int
    
    model_config = ConfigDict(from_attributes=True)