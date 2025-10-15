#!/usr/bin/env python3
"""
Script para asignar cursos al docente de prueba
"""
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.shared.models import User, RoleEnum, Curso

def asignar_cursos_docente():
    """Asigna cursos al docente de prueba"""
    db: Session = SessionLocal()
    
    try:
        print("=== ASIGNANDO CURSOS AL DOCENTE DE PRUEBA ===\n")
        
        # Buscar el docente de prueba
        docente_test = db.query(User).filter(User.dni == "87654321").first()
        if not docente_test:
            print("Docente de prueba no encontrado")
            return False
        
        print(f"Docente: {docente_test.first_name} {docente_test.last_name}")
        
        # Buscar cursos sin docente asignado
        cursos_sin_docente = db.query(Curso).filter(Curso.docente_id.is_(None)).limit(5).all()
        
        if not cursos_sin_docente:
            print("No hay cursos disponibles para asignar")
            return False
        
        print(f"Cursos disponibles: {len(cursos_sin_docente)}")
        
        # Asignar cursos al docente
        for curso in cursos_sin_docente:
            curso.docente_id = docente_test.id
            print(f"   - Asignado: {curso.nombre} ({curso.codigo})")
        
        db.commit()
        print(f"\n+ {len(cursos_sin_docente)} cursos asignados al docente")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Asignando cursos al docente de prueba...")
    if asignar_cursos_docente():
        print("\n+ ¡Cursos asignados exitosamente!")
    else:
        print("\n- Error al asignar cursos")
