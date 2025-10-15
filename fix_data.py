#!/usr/bin/env python3
"""
Script para corregir los datos en la base de datos
"""
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.shared.models import User, RoleEnum, Curso, Matricula, Ciclo

def fix_database_data():
    """Corrige los datos en la base de datos"""
    db: Session = SessionLocal()
    
    try:
        print("=== CORRIGIENDO DATOS EN LA BASE DE DATOS ===\n")
        
        # 1. Asignar códigos a los cursos
        print("1. Asignando codigos a los cursos...")
        cursos = db.query(Curso).filter(Curso.codigo.is_(None)).all()
        for i, curso in enumerate(cursos, 1):
            # Generar código basado en el ciclo y número
            ciclo_num = curso.ciclo.numero if curso.ciclo else 1
            codigo = f"DS{ciclo_num:02d}{i:03d}"
            curso.codigo = codigo
            curso.creditos = 3  # Valor por defecto
            curso.horas_semanales = 4  # Valor por defecto
            print(f"   - {curso.nombre}: {codigo}")
        
        # 2. Asignar cursos al docente de prueba
        print("\n2. Asignando cursos al docente de prueba...")
        docente_test = db.query(User).filter(User.dni == "87654321").first()
        if docente_test:
            # Asignar algunos cursos del ciclo I al docente de prueba
            cursos_ciclo_i = db.query(Curso).filter(
                Curso.ciclo.has(numero=1),
                Curso.docente_id.is_(None)
            ).limit(3).all()
            
            for curso in cursos_ciclo_i:
                curso.docente_id = docente_test.id
                print(f"   - Asignado: {curso.nombre}")
        
        # 3. Crear matrícula para el estudiante de prueba
        print("\n3. Creando matricula para el estudiante de prueba...")
        estudiante_test = db.query(User).filter(User.dni == "11223344").first()
        if estudiante_test:
            # Obtener el primer ciclo
            ciclo_i = db.query(Ciclo).filter(Ciclo.numero == 1).first()
            if ciclo_i:
                # Verificar si ya existe la matrícula
                matricula_existente = db.query(Matricula).filter(
                    Matricula.estudiante_id == estudiante_test.id,
                    Matricula.ciclo_id == ciclo_i.id
                ).first()
                
                if not matricula_existente:
                    nueva_matricula = Matricula(
                        estudiante_id=estudiante_test.id,
                        curso_id=1,  # Asignar al primer curso
                        ciclo_id=ciclo_i.id,
                        codigo_matricula=f"MAT-{estudiante_test.dni}",
                        fecha_matricula="2025-01-01",
                        estado="activa",
                        is_active=True
                    )
                    db.add(nueva_matricula)
                    print(f"   - Matricula creada para {estudiante_test.first_name} {estudiante_test.last_name}")
                else:
                    print(f"   - Matricula ya existe para {estudiante_test.first_name} {estudiante_test.last_name}")
        
        # 4. Crear algunas matrículas adicionales para estudiantes
        print("\n4. Creando matrículas adicionales...")
        estudiantes = db.query(User).filter(User.role == RoleEnum.ESTUDIANTE).limit(10).all()
        ciclo_i = db.query(Ciclo).filter(Ciclo.numero == 1).first()
        
        if ciclo_i:
            for i, estudiante in enumerate(estudiantes):
                matricula_existente = db.query(Matricula).filter(
                    Matricula.estudiante_id == estudiante.id,
                    Matricula.ciclo_id == ciclo_i.id
                ).first()
                
                if not matricula_existente:
                    nueva_matricula = Matricula(
                        estudiante_id=estudiante.id,
                        curso_id=1,
                        ciclo_id=ciclo_i.id,
                        codigo_matricula=f"MAT-{estudiante.dni}-{i}",
                        fecha_matricula="2025-01-01",
                        estado="activa",
                        is_active=True
                    )
                    db.add(nueva_matricula)
                    print(f"   - Matricula creada para {estudiante.first_name} {estudiante.last_name}")
        
        db.commit()
        print("\n+ Datos corregidos exitosamente!")
        return True
        
    except Exception as e:
        print(f"Error al corregir datos: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Corrigiendo datos en la base de datos...")
    if fix_database_data():
        print("\n+ ¡Correccion completada!")
    else:
        print("\n- Error en la correccion")
