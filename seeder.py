#!/usr/bin/env python3
"""
Seeder para poblar la base de datos con usuarios de prueba
Sistema de Notas Académico
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from datetime import datetime, date
from app.database import SessionLocal, engine, Base
from app.shared.models import User, RoleEnum, Carrera, Ciclo, Curso, Matricula, Nota, HistorialNota
from app.modules.auth.security import get_password_hash

def check_database_connection():
    """Verifica si se puede conectar a la base de datos"""
    try:
        # Intentar crear una conexión simple
        connection = engine.connect()
        connection.close()
        return True
    except OperationalError as e:
        print(f"❌ Error de conexión a la base de datos:")
        print(f"   {str(e)}")
        print("\n🔧 Posibles soluciones:")
        print("   1. Verificar que PostgreSQL esté corriendo")
        print("   2. Verificar las credenciales en el archivo .env")
        print("   3. Verificar que la base de datos 'sistema_notas' exista")
        print("   4. Verificar la configuración de red/puerto")
        return False

def create_database_structure():
    """Crea la estructura de la base de datos"""
    try:
        print("🔄 Actualizando estructura de la base de datos...")
        Base.metadata.create_all(bind=engine)
        print("✅ Estructura de base de datos actualizada")
        return True
    except Exception as e:
        print(f"❌ Error al crear la estructura de la base de datos: {e}")
        return False

def create_carrera_desarrollo_software():
    """Crea la carrera 'Desarrollo de Software' si no existe"""
    db: Session = SessionLocal()
    
    try:
        # Verificar si la carrera ya existe
        existing_carrera = db.query(Carrera).filter(
            Carrera.nombre == "Desarrollo de Software"
        ).first()
        
        if existing_carrera:
            print("⚠️  Carrera 'Desarrollo de Software' ya existe")
            return existing_carrera
        
        # Crear la carrera
        carrera_data = {
            "nombre": "Desarrollo de Software",
            "codigo": "DS",
            "descripcion": "Carrera técnica enfocada en el desarrollo de aplicaciones y sistemas de software",
            "duracion_ciclos": 6,
            "is_active": True
        }
        
        new_carrera = Carrera(**carrera_data)
        db.add(new_carrera)
        db.commit()
        db.refresh(new_carrera)
        
        print(f"✅ Carrera creada: {new_carrera.nombre} (Código: {new_carrera.codigo})")
        return new_carrera
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al crear carrera: {e}")
        raise
    finally:
        db.close()

def create_test_users():
    """Crea usuarios de prueba específicos según la imagen proporcionada"""
    db: Session = SessionLocal()
    
    try:
        # Lista de usuarios específicos de la imagen
        test_users = [
            # Administrador
            {
                "dni": "12345678",
                "email": "admin@sistema.edu",
                "password": "admin123",
                "first_name": "Carlos",
                "last_name": "Administrador",
                "phone": "987654321",
                "role": RoleEnum.ADMIN
            },
            # Docente
            {
                "dni": "87654321",
                "email": "docente@sistema.edu",
                "password": "docente123",
                "first_name": "Juan",
                "last_name": "Pérez",
                "phone": "987654322",
                "role": RoleEnum.DOCENTE
            },
            # Estudiante
            {
                "dni": "11223344",
                "email": "estudiante@sistema.edu",
                "password": "estudiante123",
                "first_name": "Pedro",
                "last_name": "López",
                "phone": "987654323",
                "role": RoleEnum.ESTUDIANTE
            }
        ]
        
        created_count = 0
        skipped_count = 0
        
        for user_data in test_users:
            # Verificar si el usuario ya existe
            existing_user = db.query(User).filter(
                (User.dni == user_data["dni"]) | (User.email == user_data["email"])
            ).first()
            
            if existing_user:
                print(f"⚠️  Usuario ya existe: {user_data['first_name']} {user_data['last_name']} (DNI: {user_data['dni']})")
                skipped_count += 1
                continue
            
            # Crear nuevo usuario con campos específicos por rol
            hashed_password = get_password_hash(user_data["password"])
            
            # Campos base para todos los usuarios
            user_fields = {
                "dni": user_data["dni"],
                "email": user_data["email"],
                "hashed_password": hashed_password,
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "phone": user_data["phone"],
                "role": user_data["role"],
                "is_active": True
            }
            
            # Agregar campos específicos según el rol
            if user_data["role"] == RoleEnum.ESTUDIANTE:
                user_fields.update({
                    "fecha_nacimiento": date(2000, 1, 1),  # Fecha ejemplo
                    "direccion": "Av. Ejemplo 123, Lima",
                    "nombre_apoderado": "María López",
                    "telefono_apoderado": "987654324"
                })
            elif user_data["role"] == RoleEnum.DOCENTE:
                user_fields.update({
                    "especialidad": "Ingeniería de Software",
                    "grado_academico": "Magíster",
                    "fecha_ingreso": date(2020, 3, 1)
                })
            
            new_user = User(**user_fields)
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            print(f"✅ Usuario creado: {new_user.first_name} {new_user.last_name} ({new_user.role.value}) - DNI: {new_user.dni}")
            created_count += 1
        
        # Resumen final
        total_users = db.query(User).count()
        print("--" * 25)
        print(f"🎉 Proceso completado:")
        print(f"   • Usuarios creados: {created_count}")
        print(f"   • Usuarios omitidos: {skipped_count}")
        print(f"   • Total en BD: {total_users}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al crear usuarios: {e}")
        raise
    finally:
        db.close()


def display_credentials():
    """Muestra las credenciales de los usuarios creados"""
    print("\n" + "=" * 60)
    print("📋 CREDENCIALES DE USUARIOS DE PRUEBA")
    print("=" * 60)
    
    print("\n🔑 ADMINISTRADOR:")
    print("   DNI: 12345678 | Email: admin@sistema.edu | Password: admin123")
    
    print("\n👨‍🏫 DOCENTE:")
    print("   DNI: 87654321 | Email: docente@sistema.edu | Password: docente123")
    
    print("\n🎓 ESTUDIANTE:")
    print("   DNI: 11223344 | Email: estudiante@sistema.edu | Password: estudiante123")
    
    print("\n💡 NOTA: Puedes usar el DNI o email para iniciar sesión desde el cliente.")
    print("=" * 60)
    
    print("\n🚀 ¡Listo! Ahora puedes iniciar sesión desde tu cliente React.")
    print("   Frontend: http://localhost:5173")
    print("   Backend API: http://localhost:9001")
    print("   Documentación: http://localhost:9001/docs")

if __name__ == "__main__":
    print("🚀 Iniciando seeder del Sistema de Notas...")
    
    # Verificar conexión a la base de datos
    if not check_database_connection():
        print("\n❌ No se puede conectar a la base de datos. Seeder cancelado.")
        exit(1)
    
    # Crear estructura de la base de datos
    if not create_database_structure():
        print("\n❌ No se pudo crear la estructura de la base de datos. Seeder cancelado.")
        exit(1)
    
    # Crear carrera 'Desarrollo de Software'
    create_carrera_desarrollo_software()
    
    # Crear usuarios de prueba
    create_test_users()
    
    # Mostrar credenciales
    display_credentials()