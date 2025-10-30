from decimal import Decimal
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.shared.models import Nota


class GradeCalculator:
    """Calculadora de calificaciones según el sistema específico del ciclo de 4 meses"""
    
    # Constantes del sistema - PESOS CORRECTOS
    PESO_EVALUACIONES = Decimal('0.1')     # 10% - Evaluaciones semanales
    PESO_PRACTICAS = Decimal('0.3')        # 30% - Prácticas
    PESO_PARCIALES = Decimal('0.6')        # 60% - Parciales
    
    NOTA_MINIMA_APROBACION = Decimal('13.0')
    
    @classmethod
    def calcular_promedio_evaluaciones(cls, nota: Nota) -> Optional[Decimal]:
        """Calcula el promedio de las evaluaciones semanales (1-8)"""
        evaluaciones = []
        for i in range(1, 9):
            eval_val = getattr(nota, f'evaluacion{i}')
            if eval_val is not None and float(eval_val) > 0:
                evaluaciones.append(Decimal(str(eval_val)))
        return cls._calcular_promedio_lista(evaluaciones)
    
    @classmethod
    def calcular_promedio_practicas(cls, nota: Nota) -> Optional[Decimal]:
        """Calcula el promedio de las prácticas (1-4)"""
        practicas = []
        for i in range(1, 5):
            prac_val = getattr(nota, f'practica{i}')
            if prac_val is not None and float(prac_val) > 0:
                practicas.append(Decimal(str(prac_val)))
        return cls._calcular_promedio_lista(practicas)
    
    @classmethod
    def calcular_promedio_parciales(cls, nota: Nota) -> Optional[Decimal]:
        """Calcula el promedio de los parciales (1-2)"""
        parciales = []
        for i in range(1, 3):
            parc_val = getattr(nota, f'parcial{i}')
            if parc_val is not None and float(parc_val) > 0:
                parciales.append(Decimal(str(parc_val)))
        return cls._calcular_promedio_lista(parciales)

    @classmethod
    def calcular_promedio_nota(cls, nota: Nota) -> Optional[Decimal]:
        """
        Calcula el promedio final de una nota individual con los pesos correctos:
        - Evaluaciones 1-8: 10%
        - Prácticas 1-4: 30%  
        - Parciales 1-2: 60%
        """
        # Calcular promedio de evaluaciones
        evaluaciones = []
        for i in range(1, 9):
            eval_val = getattr(nota, f'evaluacion{i}')
            if eval_val is not None and float(eval_val) > 0:
                evaluaciones.append(Decimal(str(eval_val)))
        
        # Calcular promedio de prácticas
        practicas = []
        for i in range(1, 5):
            prac_val = getattr(nota, f'practica{i}')
            if prac_val is not None and float(prac_val) > 0:
                practicas.append(Decimal(str(prac_val)))
        
        # Calcular promedio de parciales
        parciales = []
        for i in range(1, 3):
            parc_val = getattr(nota, f'parcial{i}')
            if parc_val is not None and float(parc_val) > 0:
                parciales.append(Decimal(str(parc_val)))
        
        # Calcular promedios por categoría
        prom_evaluaciones = cls._calcular_promedio_lista(evaluaciones)
        prom_practicas = cls._calcular_promedio_lista(practicas)
        prom_parciales = cls._calcular_promedio_lista(parciales)
        
        # Solo calcular promedio final si hay al menos una nota en cada categoría
        if prom_evaluaciones > 0 and prom_practicas > 0 and prom_parciales > 0:
            promedio_final = (
                prom_evaluaciones * cls.PESO_EVALUACIONES +
                prom_practicas * cls.PESO_PRACTICAS +
                prom_parciales * cls.PESO_PARCIALES
            )
            return round(promedio_final, 2)
        
        return None
    
    @classmethod
    def calcular_promedio_final(cls, estudiante_id: int, curso_id: int, db: Session) -> Dict:
        """
        Calcula el promedio final de un estudiante en un curso específico
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
                    'promedio_evaluaciones': Decimal('0.00'),
                    'promedio_practicas': Decimal('0.00'),
                    'promedio_parciales': Decimal('0.00'),
                    'notas_evaluaciones': [],
                    'notas_practicas': [],
                    'notas_parciales': []
                }
            }
        
        # Recopilar todas las notas por categoría
        todas_evaluaciones = []
        todas_practicas = []
        todos_parciales = []
        
        for nota in notas:
            # Evaluaciones semanales (evaluacion1-8)
            for i in range(1, 9):
                eval_field = getattr(nota, f'evaluacion{i}', None)
                if eval_field is not None and float(eval_field) > 0:
                    todas_evaluaciones.append(Decimal(str(eval_field)))
            
            # Prácticas (practica1-4)
            for i in range(1, 5):
                prac_field = getattr(nota, f'practica{i}', None)
                if prac_field is not None and float(prac_field) > 0:
                    todas_practicas.append(Decimal(str(prac_field)))
            
            # Parciales (parcial1-2)
            for i in range(1, 3):
                parc_field = getattr(nota, f'parcial{i}', None)
                if parc_field is not None and float(parc_field) > 0:
                    todos_parciales.append(Decimal(str(parc_field)))
        
        # Calcular promedios por tipo
        promedio_evaluaciones = cls._calcular_promedio_lista(todas_evaluaciones)
        promedio_practicas = cls._calcular_promedio_lista(todas_practicas)
        promedio_parciales = cls._calcular_promedio_lista(todos_parciales)
        
        # Calcular promedio final ponderado
        promedio_final = Decimal('0.00')
        if promedio_evaluaciones > 0 and promedio_practicas > 0 and promedio_parciales > 0:
            promedio_final = (
                promedio_evaluaciones * cls.PESO_EVALUACIONES +
                promedio_practicas * cls.PESO_PRACTICAS +
                promedio_parciales * cls.PESO_PARCIALES
            )
            promedio_final = round(promedio_final, 2)
        
        # Determinar estado
        if promedio_final >= cls.NOTA_MINIMA_APROBACION:
            estado = "APROBADO"
        elif promedio_final > 0:
            estado = "DESAPROBADO"
        else:
            estado = "PENDIENTE"
        
        return {
            'promedio_final': promedio_final,
            'estado': estado,
            'detalle': {
                'promedio_evaluaciones': promedio_evaluaciones,
                'promedio_practicas': promedio_practicas,
                'promedio_parciales': promedio_parciales,
                'notas_evaluaciones': todas_evaluaciones,
                'notas_practicas': todas_practicas,
                'notas_parciales': todos_parciales
            }
        }
    
    @classmethod
    def calcular_promedio_curso(cls, db: Session, curso_id: int) -> Optional[Decimal]:
        """
        Calcula el promedio general de un curso basado en todas las notas de sus estudiantes
        """
        notas = db.query(Nota).filter(Nota.curso_id == curso_id).all()
        promedios_estudiantes = []
        
        for nota in notas:
            promedio = cls.calcular_promedio_nota(nota)
            if promedio is not None:
                promedios_estudiantes.append(promedio)
        
        if promedios_estudiantes:
            return cls._calcular_promedio_lista(promedios_estudiantes)
        return None
    
    @classmethod
    def contar_notas_por_rango(cls, db: Session, rango_min: float, rango_max: float = None) -> int:
        """
        Cuenta las notas que están en un rango específico
        """
        notas = db.query(Nota).all()
        contador = 0
        
        for nota in notas:
            promedio = cls.calcular_promedio_nota(nota)
            if promedio is not None:
                promedio_float = float(promedio)
                if rango_max is None:
                    if promedio_float >= rango_min:
                        contador += 1
                else:
                    if rango_min <= promedio_float < rango_max:
                        contador += 1
        
        return contador
    
    @classmethod
    def obtener_notas_con_promedio(cls, db: Session, filtros: dict = None) -> List[dict]:
        """
        Obtiene todas las notas con sus promedios calculados
        """
        query = db.query(Nota)
        
        if filtros:
            if 'curso_id' in filtros:
                query = query.filter(Nota.curso_id == filtros['curso_id'])
            if 'estudiante_id' in filtros:
                query = query.filter(Nota.estudiante_id == filtros['estudiante_id'])
        
        notas = query.all()
        resultado = []
        
        for nota in notas:
            promedio = cls.calcular_promedio_nota(nota)
            if promedio is not None:
                resultado.append({
                    'nota': nota,
                    'promedio_calculado': float(promedio)
                })
        
        return resultado
    
    @classmethod
    def _calcular_promedio_lista(cls, valores: List[Decimal]) -> Decimal:
        """Calcula el promedio de una lista de valores"""
        if not valores:
            return Decimal('0.00')
        
        suma = sum(valores)
        promedio = suma / len(valores)
        return round(promedio, 2)
    
    @classmethod
    def validar_estructura_ciclo(cls, estudiante_id: int, curso_id: int, db: Session) -> Dict:
        """
        Valida que el estudiante tenga la estructura correcta de notas:
        - 8 evaluaciones semanales
        - 4 prácticas
        - 2 parciales
        """
        notas = db.query(Nota).filter(
            Nota.estudiante_id == estudiante_id,
            Nota.curso_id == curso_id
        ).all()
        
        if not notas:
            return {
                'valido': False,
                'mensaje': 'No se encontraron notas para el estudiante en este curso'
            }
        
        # Contar notas por categoría
        evaluaciones_count = 0
        practicas_count = 0
        parciales_count = 0
        
        for nota in notas:
            for i in range(1, 9):
                if getattr(nota, f'evaluacion{i}') is not None:
                    evaluaciones_count += 1
            
            for i in range(1, 5):
                if getattr(nota, f'practica{i}') is not None:
                    practicas_count += 1
            
            for i in range(1, 3):
                if getattr(nota, f'parcial{i}') is not None:
                    parciales_count += 1
        
        return {
            'valido': evaluaciones_count > 0 and practicas_count > 0 and parciales_count > 0,
            'evaluaciones': evaluaciones_count,
            'practicas': practicas_count,
            'parciales': parciales_count,
            'mensaje': f'Evaluaciones: {evaluaciones_count}, Prácticas: {practicas_count}, Parciales: {parciales_count}'
        }
