#!/usr/bin/env python3
"""
Seeder para poblar la base de datos con usuarios de prueba
Sistema de Notas Académico
"""
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.database import SessionLocal, engine, Base
from app.shared import User, RoleEnum, Carrera, Ciclo, Curso, Matricula, Nota, HistorialNota
from app.modules.auth.security import get_password_hash

# Crear todas las tablas si no existen
Base.metadata.create_all(bind=engine)

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
            
            # Crear nuevo usuario
            hashed_password = get_password_hash(user_data["password"])
            new_user = User(
                dni=user_data["dni"],
                email=user_data["email"],
                hashed_password=hashed_password,
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                phone=user_data["phone"],
                role=user_data["role"],
                is_active=True
            )
            
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
    print("🌱 SEEDER - Sistema de Notas Académico")
    print("="*40)
    
    try:
        create_test_users()
        display_credentials()
        
    except Exception as e:
        print(f"\n❌ Error fatal: {str(e)}")
        exit(1)