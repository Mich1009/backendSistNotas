"""
Utilidades para cálculo de promedios de notas - DEPRECADO
Este archivo se mantiene por compatibilidad pero se recomienda usar GradeCalculator
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from .models import Nota
from .grade_calculator import GradeCalculator


def calcular_promedio_nota(nota: Nota) -> Optional[float]:
    """
    DEPRECADO: Usar GradeCalculator.calcular_promedio_nota() en su lugar
    Calcula el promedio de una nota individual usando GradeCalculator
    """
    promedio = GradeCalculator.calcular_promedio_nota(nota)
    return float(promedio) if promedio is not None else None


def calcular_promedio_curso(db: Session, curso_id: int) -> Optional[float]:
    """
    DEPRECADO: Usar GradeCalculator.calcular_promedio_curso() en su lugar
    Calcula el promedio general de un curso usando GradeCalculator
    """
    promedio = GradeCalculator.calcular_promedio_curso(db, curso_id)
    return float(promedio) if promedio is not None else None


def obtener_notas_con_promedio(db: Session, filtros: dict = None) -> List[dict]:
    """
    DEPRECADO: Usar GradeCalculator.obtener_notas_con_promedio() en su lugar
    Obtiene todas las notas con sus promedios calculados usando GradeCalculator
    """
    return GradeCalculator.obtener_notas_con_promedio(db, filtros)


def contar_notas_por_rango(db: Session, rango_min: float, rango_max: float = None) -> int:
    """
    DEPRECADO: Usar GradeCalculator.contar_notas_por_rango() en su lugar
    Cuenta las notas que están en un rango específico usando GradeCalculator
    """
    return GradeCalculator.contar_notas_por_rango(db, rango_min, rango_max)