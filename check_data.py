#!/usr/bin/env python3
"""
Script para verificar que todos los datos estén correctamente en la base de datos
"""
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.shared.models import User, RoleEnum, Carrera, Ciclo, Curso, Matricula, Nota

def check_database_data():
    """Verifica que todos los datos estén en la base de datos"""
    db: Session = SessionLocal()
    
    try:
        print("=== VERIFICACION DE DATOS EN LA BASE DE DATOS ===\n")
        
        # Verificar usuarios
        print("1. USUARIOS:")
        users = db.query(User).all()
        print(f"   Total usuarios: {len(users)}")
        
        admins = db.query(User).filter(User.role == RoleEnum.ADMIN).all()
        docentes = db.query(User).filter(User.role == RoleEnum.DOCENTE).all()
        estudiantes = db.query(User).filter(User.role == RoleEnum.ESTUDIANTE).all()
        
        print(f"   - Administradores: {len(admins)}")
        for admin in admins:
            print(f"     * {admin.dni} - {admin.first_name} {admin.last_name} ({admin.email})")
        
        print(f"   - Docentes: {len(docentes)}")
        for docente in docentes[:5]:  # Mostrar solo los primeros 5
            print(f"     * {docente.dni} - {docente.first_name} {docente.last_name} ({docente.email})")
        if len(docentes) > 5:
            print(f"     ... y {len(docentes) - 5} más")
        
        print(f"   - Estudiantes: {len(estudiantes)}")
        for estudiante in estudiantes[:5]:  # Mostrar solo los primeros 5
            print(f"     * {estudiante.dni} - {estudiante.first_name} {estudiante.last_name} ({estudiante.email})")
        if len(estudiantes) > 5:
            print(f"     ... y {len(estudiantes) - 5} más")
        
        # Verificar carreras
        print("\n2. CARRERAS:")
        carreras = db.query(Carrera).all()
        print(f"   Total carreras: {len(carreras)}")
        for carrera in carreras:
            print(f"   - {carrera.codigo}: {carrera.nombre}")
        
        # Verificar ciclos
        print("\n3. CICLOS:")
        ciclos = db.query(Ciclo).all()
        print(f"   Total ciclos: {len(ciclos)}")
        for ciclo in ciclos:
            print(f"   - {ciclo.nombre} ({ciclo.año}) - {ciclo.carrera.nombre if ciclo.carrera else 'Sin carrera'}")
        
        # Verificar cursos
        print("\n4. CURSOS:")
        cursos = db.query(Curso).all()
        print(f"   Total cursos: {len(cursos)}")
        for curso in cursos[:10]:  # Mostrar solo los primeros 10
            docente_nombre = f"{curso.docente.first_name} {curso.docente.last_name}" if curso.docente else "Sin docente"
            print(f"   - {curso.nombre} ({curso.codigo}) - Docente: {docente_nombre} - Ciclo: {curso.ciclo.nombre}")
        if len(cursos) > 10:
            print(f"   ... y {len(cursos) - 10} más")
        
        # Verificar matrículas
        print("\n5. MATRICULAS:")
        matriculas = db.query(Matricula).all()
        print(f"   Total matrículas: {len(matriculas)}")
        
        # Verificar notas
        print("\n6. NOTAS:")
        notas = db.query(Nota).all()
        print(f"   Total notas: {len(notas)}")
        
        # Verificar datos específicos para cada rol
        print("\n=== VERIFICACION POR ROLES ===")
        
        # Verificar docente específico
        docente_test = db.query(User).filter(User.dni == "87654321").first()
        if docente_test:
            print(f"\nDOCENTE DE PRUEBA ({docente_test.dni}):")
            cursos_docente = db.query(Curso).filter(Curso.docente_id == docente_test.id).all()
            print(f"   Cursos asignados: {len(cursos_docente)}")
            for curso in cursos_docente:
                print(f"   - {curso.nombre} ({curso.codigo})")
        
        # Verificar estudiante específico
        estudiante_test = db.query(User).filter(User.dni == "11223344").first()
        if estudiante_test:
            print(f"\nESTUDIANTE DE PRUEBA ({estudiante_test.dni}):")
            matriculas_estudiante = db.query(Matricula).filter(Matricula.estudiante_id == estudiante_test.id).all()
            print(f"   Matrículas: {len(matriculas_estudiante)}")
            for matricula in matriculas_estudiante:
                print(f"   - Ciclo: {matricula.ciclo.nombre}")
        
        print("\n=== RESUMEN ===")
        print(f"+ Usuarios: {len(users)}")
        print(f"+ Carreras: {len(carreras)}")
        print(f"+ Ciclos: {len(ciclos)}")
        print(f"+ Cursos: {len(cursos)}")
        print(f"+ Matriculas: {len(matriculas)}")
        print(f"+ Notas: {len(notas)}")
        
        if len(users) > 0 and len(carreras) > 0 and len(ciclos) > 0 and len(cursos) > 0:
            print("\n+ BASE DE DATOS CON DATOS COMPLETOS")
            return True
        else:
            print("\n- BASE DE DATOS INCOMPLETA")
            return False
            
    except Exception as e:
        print(f"Error al verificar datos: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Verificando datos en la base de datos...")
    if check_database_data():
        print("\n+ ¡Todos los datos estan presentes!")
    else:
        print("\n- Faltan datos en la base de datos")
