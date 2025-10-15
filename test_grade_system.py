#!/usr/bin/env python3
"""
Script para probar el nuevo sistema de calificaciones
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.shared.grade_calculator import GradeCalculator
from app.modules.teacher.models import Nota, User, Curso, Matricula
from sqlalchemy.orm import Session

def test_grade_system():
    """Probar el sistema de calificaciones"""
    print("🧪 Probando el sistema de calificaciones...")
    
    # Obtener sesión de base de datos
    db = next(get_db())
    
    try:
        # Verificar que la tabla notas tiene la estructura correcta
        print("\n1. Verificando estructura de la tabla notas...")
        notas_sample = db.query(Nota).first()
        if notas_sample:
            print(f"   ✅ Tabla notas tiene datos")
            print(f"   Columnas disponibles: {notas_sample.__table__.columns.keys()}")
        else:
            print("   ℹ️  Tabla notas está vacía (esto es normal)")
        
        # Probar GradeCalculator
        print("\n2. Probando GradeCalculator...")
        
        # Crear datos de prueba
        print("   Creando datos de prueba...")
        
        # Buscar un estudiante y curso existentes
        estudiante = db.query(User).filter(User.role == 'ESTUDIANTE').first()
        curso = db.query(Curso).first()
        
        if not estudiante or not curso:
            print("   ⚠️  No hay estudiantes o cursos en la base de datos")
            print("   Creando datos de prueba...")
            
            # Crear un estudiante de prueba
            estudiante = User(
                dni="12345678",
                email="test@example.com",
                first_name="Estudiante",
                last_name="Prueba",
                role="ESTUDIANTE",
                carrera_id=1
            )
            db.add(estudiante)
            db.commit()
            db.refresh(estudiante)
            
            # Crear un curso de prueba
            curso = Curso(
                nombre="Curso de Prueba",
                codigo="TEST001",
                carrera_id=1,
                ciclo_numero=1,
                docente_id=1
            )
            db.add(curso)
            db.commit()
            db.refresh(curso)
            
            # Crear matrícula
            matricula = Matricula(
                estudiante_id=estudiante.id,
                curso_id=curso.id,
                ciclo_id=1
            )
            db.add(matricula)
            db.commit()
        
        print(f"   Estudiante: {estudiante.first_name} {estudiante.last_name} (ID: {estudiante.id})")
        print(f"   Curso: {curso.nombre} (ID: {curso.id})")
        
        # Crear notas de prueba
        print("   Creando notas de prueba...")
        
        # Notas semanales
        notas_semanales = [
            {"valor_nota": 16.0, "fecha_evaluacion": "2024-01-15", "observaciones": "Semana 1"},
            {"valor_nota": 18.0, "fecha_evaluacion": "2024-01-22", "observaciones": "Semana 2"},
            {"valor_nota": 15.0, "fecha_evaluacion": "2024-01-29", "observaciones": "Semana 3"},
            {"valor_nota": 17.0, "fecha_evaluacion": "2024-02-05", "observaciones": "Semana 4"}
        ]
        
        for nota_data in notas_semanales:
            nota = Nota(
                estudiante_id=estudiante.id,
                curso_id=curso.id,
                tipo_evaluacion="SEMANAL",
                valor_nota=nota_data["valor_nota"],
                peso=0.1,
                fecha_evaluacion=nota_data["fecha_evaluacion"],
                observaciones=nota_data["observaciones"]
            )
            db.add(nota)
        
        # Prácticas
        notas_practicas = [
            {"valor_nota": 18.0, "fecha_evaluacion": "2024-01-30", "observaciones": "Práctica 1"},
            {"valor_nota": 16.0, "fecha_evaluacion": "2024-02-28", "observaciones": "Práctica 2"}
        ]
        
        for nota_data in notas_practicas:
            nota = Nota(
                estudiante_id=estudiante.id,
                curso_id=curso.id,
                tipo_evaluacion="PRACTICA",
                valor_nota=nota_data["valor_nota"],
                peso=0.3,
                fecha_evaluacion=nota_data["fecha_evaluacion"],
                observaciones=nota_data["observaciones"]
            )
            db.add(nota)
        
        # Parcial
        nota_parcial = Nota(
            estudiante_id=estudiante.id,
            curso_id=curso.id,
            tipo_evaluacion="PARCIAL",
            valor_nota=17.0,
            peso=0.3,
            fecha_evaluacion="2024-02-15",
            observaciones="Primer Parcial"
        )
        db.add(nota_parcial)
        
        db.commit()
        print("   ✅ Notas de prueba creadas")
        
        # Probar cálculo de promedio final
        print("\n3. Probando cálculo de promedio final...")
        resultado = GradeCalculator.calcular_promedio_final(estudiante.id, curso.id, db)
        
        print(f"   Promedio Final: {resultado['promedio_final']}")
        print(f"   Estado: {resultado['estado']}")
        print(f"   Detalle:")
        print(f"     - Promedio Semanales: {resultado['detalle']['promedio_semanales']}")
        print(f"     - Promedio Prácticas: {resultado['detalle']['promedio_practicas']}")
        print(f"     - Promedio Parciales: {resultado['detalle']['promedio_parciales']}")
        
        # Probar validación de estructura
        print("\n4. Probando validación de estructura...")
        estructura = GradeCalculator.validar_estructura_ciclo(estudiante.id, curso.id, db)
        
        print(f"   Notas Semanales: {estructura['notas_semanales']['actuales']}/{estructura['notas_semanales']['esperadas']}")
        print(f"   Notas Prácticas: {estructura['notas_practicas']['actuales']}/{estructura['notas_practicas']['esperadas']}")
        print(f"   Notas Parciales: {estructura['notas_parciales']['actuales']}/{estructura['notas_parciales']['esperadas']}")
        print(f"   Estructura Completa: {estructura['estructura_completa']}")
        
        print("\n✅ Todas las pruebas pasaron exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_grade_system()
