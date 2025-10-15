#!/usr/bin/env python3
"""
Script para crear cursos específicos para el docente de prueba
"""
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.shared.models import User, RoleEnum, Curso, Ciclo

def crear_cursos_docente():
    """Crea cursos específicos para el docente de prueba"""
    db: Session = SessionLocal()
    
    try:
        print("=== CREANDO CURSOS PARA EL DOCENTE DE PRUEBA ===\n")
        
        # Buscar el docente de prueba
        docente_test = db.query(User).filter(User.dni == "87654321").first()
        if not docente_test:
            print("Docente de prueba no encontrado")
            return False
        
        print(f"Docente: {docente_test.first_name} {docente_test.last_name}")
        
        # Buscar el primer ciclo
        ciclo_i = db.query(Ciclo).filter(Ciclo.numero == 1).first()
        if not ciclo_i:
            print("Ciclo I no encontrado")
            return False
        
        print(f"Ciclo: {ciclo_i.nombre}")
        
        # Crear cursos específicos para el docente de prueba
        cursos_nuevos = [
            {
                "nombre": "Programación Web I",
                "codigo": "PW001",
                "descripcion": "Curso de programación web básica",
                "creditos": 4,
                "horas_semanales": 6
            },
            {
                "nombre": "Base de Datos I",
                "codigo": "BD001",
                "descripcion": "Curso de base de datos relacionales",
                "creditos": 3,
                "horas_semanales": 4
            },
            {
                "nombre": "Algoritmos y Estructuras de Datos",
                "codigo": "AED001",
                "descripcion": "Curso de algoritmos y estructuras de datos",
                "creditos": 4,
                "horas_semanales": 6
            }
        ]
        
        cursos_creados = 0
        for curso_data in cursos_nuevos:
            # Verificar si el curso ya existe
            curso_existente = db.query(Curso).filter(Curso.codigo == curso_data["codigo"]).first()
            if curso_existente:
                print(f"   - Curso {curso_data['nombre']} ya existe")
                continue
            
            # Crear nuevo curso
            nuevo_curso = Curso(
                nombre=curso_data["nombre"],
                codigo=curso_data["codigo"],
                descripcion=curso_data["descripcion"],
                creditos=curso_data["creditos"],
                horas_semanales=curso_data["horas_semanales"],
                ciclo_id=ciclo_i.id,
                docente_id=docente_test.id,
                is_active=True
            )
            
            db.add(nuevo_curso)
            cursos_creados += 1
            print(f"   - Creado: {curso_data['nombre']} ({curso_data['codigo']})")
        
        db.commit()
        print(f"\n+ {cursos_creados} cursos creados para el docente")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Creando cursos para el docente de prueba...")
    if crear_cursos_docente():
        print("\n+ ¡Cursos creados exitosamente!")
    else:
        print("\n- Error al crear cursos")
