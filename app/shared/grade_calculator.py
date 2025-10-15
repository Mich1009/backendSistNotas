from decimal import Decimal
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.shared.models import Nota


class GradeCalculator:
    """Calculadora de calificaciones según el sistema específico del ciclo de 4 meses"""
    
    # Constantes del sistema
    PESO_NOTAS_SEMANALES = Decimal('0.1')  # 10%
    PESO_PRACTICAS = Decimal('0.3')        # 30%
    PESO_PARCIALES = Decimal('0.3')        # 30%
    
    TIPOS_EVALUACION = {
        'SEMANAL': 'SEMANAL',
        'PRACTICA': 'PRACTICA', 
        'PARCIAL': 'PARCIAL'
    }
    
    @classmethod
    def calcular_promedio_final(cls, estudiante_id: int, curso_id: int, db: Session) -> Dict:
        """
        Calcula el promedio final según la estructura:
        - Notas semanales: promedio de todas × 0.1
        - Prácticas: promedio de todas × 0.3  
        - Parciales: promedio de todas × 0.3
        - Promedio final: suma de los 3 promedios ponderados
        """
        
        # Obtener todas las notas del estudiante en el curso
        notas = db.query(Nota).filter(
            Nota.estudiante_id == estudiante_id,
            Nota.curso_id == curso_id
        ).all()
        
        if not notas:
            return {
                'promedio_final': Decimal('0.00'),
                'estado': 'SIN_NOTAS',
                'detalle': {
                    'promedio_semanales': Decimal('0.00'),
                    'promedio_practicas': Decimal('0.00'),
                    'promedio_parciales': Decimal('0.00'),
                    'notas_semanales': [],
                    'notas_practicas': [],
                    'notas_parciales': []
                }
            }
        
        # Separar notas por tipo
        notas_semanales = [n for n in notas if n.tipo_evaluacion == cls.TIPOS_EVALUACION['SEMANAL']]
        notas_practicas = [n for n in notas if n.tipo_evaluacion == cls.TIPOS_EVALUACION['PRACTICA']]
        notas_parciales = [n for n in notas if n.tipo_evaluacion == cls.TIPOS_EVALUACION['PARCIAL']]
        
        # Calcular promedios por tipo
        promedio_semanales = cls._calcular_promedio_tipo(notas_semanales)
        promedio_practicas = cls._calcular_promedio_tipo(notas_practicas)
        promedio_parciales = cls._calcular_promedio_tipo(notas_parciales)
        
        # Calcular promedio final ponderado
        promedio_final = (
            promedio_semanales * cls.PESO_NOTAS_SEMANALES +
            promedio_practicas * cls.PESO_PRACTICAS +
            promedio_parciales * cls.PESO_PARCIALES
        )
        
        promedio_final = round(promedio_final, 2)
        
        # Determinar estado
        estado = "APROBADO" if promedio_final >= Decimal('10.5') else "DESAPROBADO"
        
        return {
            'promedio_final': promedio_final,
            'estado': estado,
            'detalle': {
                'promedio_semanales': promedio_semanales,
                'promedio_practicas': promedio_practicas,
                'promedio_parciales': promedio_parciales,
                'notas_semanales': [{'id': n.id, 'valor': n.valor_nota, 'fecha': n.fecha_evaluacion} for n in notas_semanales],
                'notas_practicas': [{'id': n.id, 'valor': n.valor_nota, 'fecha': n.fecha_evaluacion} for n in notas_practicas],
                'notas_parciales': [{'id': n.id, 'valor': n.valor_nota, 'fecha': n.fecha_evaluacion} for n in notas_parciales]
            }
        }
    
    @classmethod
    def _calcular_promedio_tipo(cls, notas: List[Nota]) -> Decimal:
        """Calcula el promedio de un tipo específico de notas"""
        if not notas:
            return Decimal('0.00')
        
        suma = sum(nota.valor_nota for nota in notas)
        promedio = suma / len(notas)
        return round(promedio, 2)
    
    @classmethod
    def validar_estructura_ciclo(cls, estudiante_id: int, curso_id: int, db: Session) -> Dict:
        """
        Valida que el estudiante tenga la estructura correcta de notas:
        - 32 notas semanales (8 por mes × 4 meses)
        - 4 prácticas (1 por mes)
        - 2 parciales (1 cada 2 meses)
        """
        
        notas = db.query(Nota).filter(
            Nota.estudiante_id == estudiante_id,
            Nota.curso_id == curso_id
        ).all()
        
        notas_semanales = [n for n in notas if n.tipo_evaluacion == cls.TIPOS_EVALUACION['SEMANAL']]
        notas_practicas = [n for n in notas if n.tipo_evaluacion == cls.TIPOS_EVALUACION['PRACTICA']]
        notas_parciales = [n for n in notas if n.tipo_evaluacion == cls.TIPOS_EVALUACION['PARCIAL']]
        
        return {
            'notas_semanales': {
                'esperadas': 32,
                'actuales': len(notas_semanales),
                'completas': len(notas_semanales) == 32
            },
            'notas_practicas': {
                'esperadas': 4,
                'actuales': len(notas_practicas),
                'completas': len(notas_practicas) == 4
            },
            'notas_parciales': {
                'esperadas': 2,
                'actuales': len(notas_parciales),
                'completas': len(notas_parciales) == 2
            },
            'estructura_completa': (
                len(notas_semanales) == 32 and 
                len(notas_practicas) == 4 and 
                len(notas_parciales) == 2
            )
        }
    
    @classmethod
    def obtener_peso_por_tipo(cls, tipo_evaluacion: str) -> Decimal:
        """Obtiene el peso correspondiente según el tipo de evaluación"""
        pesos = {
            cls.TIPOS_EVALUACION['SEMANAL']: cls.PESO_NOTAS_SEMANALES,
            cls.TIPOS_EVALUACION['PRACTICA']: cls.PESO_PRACTICAS,
            cls.TIPOS_EVALUACION['PARCIAL']: cls.PESO_PARCIALES
        }
        return pesos.get(tipo_evaluacion, Decimal('0.0'))
