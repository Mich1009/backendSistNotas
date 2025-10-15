#!/usr/bin/env python3
"""
Script para corregir las matrículas y relacionarlas correctamente con los cursos
"""
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.shared.models import User, RoleEnum, Curso, Matricula, Ciclo

def corregir_matriculas():
    """Corrige las matrículas para que estén relacionadas correctamente con los cursos"""
    db: Session = SessionLocal()
    
    try:
        print("=== CORRIGIENDO MATRICULAS ===\n")
        
        # Obtener todas las matrículas existentes
        matriculas = db.query(Matricula).all()
        print(f"Matrículas existentes: {len(matriculas)}")
        
        # Obtener el primer curso de cada ciclo
        ciclos = db.query(Ciclo).all()
        cursos_por_ciclo = {}
        
        for ciclo in ciclos:
            primer_curso = db.query(Curso).filter(
                Curso.ciclo_id == ciclo.id,
                Curso.is_active == True
            ).first()
            
            if primer_curso:
                cursos_por_ciclo[ciclo.id] = primer_curso.id
                print(f"Ciclo {ciclo.nombre}: Curso {primer_curso.nombre} (ID: {primer_curso.id})")
        
        # Actualizar matrículas para asignar curso_id
        actualizadas = 0
        for matricula in matriculas:
            if matricula.curso_id is None and matricula.ciclo_id in cursos_por_ciclo:
                matricula.curso_id = cursos_por_ciclo[matricula.ciclo_id]
                actualizadas += 1
                print(f"   - Matrícula {matricula.id}: Asignado curso {matricula.curso_id}")
        
        db.commit()
        print(f"\n+ {actualizadas} matrículas actualizadas")
        
        # Verificar resultado
        print("\n=== VERIFICACION ===")
        matriculas_con_curso = db.query(Matricula).filter(Matricula.curso_id.isnot(None)).count()
        print(f"Matrículas con curso asignado: {matriculas_con_curso}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Corrigiendo matrículas...")
    if corregir_matriculas():
        print("\n+ ¡Matrículas corregidas exitosamente!")
    else:
        print("\n- Error al corregir matrículas")
