#!/usr/bin/env python3
"""
Seeder para poblar la base de datos con usuarios de prueba - Versión PostgreSQL
Sistema de Notas Académico - Manejo robusto de codificación
"""

import sys
import os
from pathlib import Path

# Configurar la codificación antes de importar cualquier cosa
os.environ["PGCLIENTENCODING"] = "UTF8"
os.environ["PYTHONIOENCODING"] = "utf-8"

# Configurar sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import OperationalError
from datetime import datetime, date
import pandas as pd
import re
import psycopg2
from urllib.parse import quote_plus

# Configurar psycopg2 para UTF-8
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

# Importar modelos después de configurar codificación
from app.shared.models import User, RoleEnum, Carrera, Ciclo, Matricula, Curso, Base
from app.modules.auth.security import get_password_hash


class DatabaseManager:
    """Maneja la conexión a la base de datos con codificación robusta"""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._setup_connection()

    def _setup_connection(self):
        """Configura la conexión a la base de datos con manejo de codificación"""
        # Datos de conexión
        username = "postgres"
        password = "1234"
        host = "localhost"
        port = "5432"
        database = "sistema_notas"

        # URL encode la contraseña para manejar caracteres especiales
        password_encoded = quote_plus(password)

        # Crear URL de conexión con configuración UTF-8
        database_url = (
            f"postgresql://{username}:{password_encoded}@{host}:{port}/{database}"
        )

        try:
            # Crear engine con configuración de codificación explícita
            self.engine = create_engine(
                database_url,
                echo=False,
                pool_pre_ping=True,
                connect_args={
                    "client_encoding": "utf8",
                    "options": "-c client_encoding=utf8",
                },
            )

            # Crear sessionmaker
            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )

        except Exception as e:
            print(f"Error configurando conexión: {e}")
            raise

    def test_connection(self):
        """Prueba la conexión a la base de datos"""
        try:
            with self.engine.connect() as connection:
                # Forzar UTF-8 en la conexión
                connection.execute(text("SET client_encoding = 'UTF8'"))
                result = connection.execute(text("SELECT 1 as test"))
                return result.fetchone() is not None
        except Exception as e:
            print(f"Error en test de conexión: {e}")
            return False

    def create_tables(self):
        """Crea las tablas de la base de datos"""
        try:
            Base.metadata.create_all(bind=self.engine)
            return True
        except Exception as e:
            print(f"Error creando tablas: {e}")
            return False

    def get_session(self):
        """Obtiene una sesión de base de datos"""
        session = self.SessionLocal()
        # Forzar UTF-8 en cada sesión
        session.execute(text("SET client_encoding = 'UTF8'"))
        return session


# Instancia global del manager
db_manager = DatabaseManager()


def check_database_connection():
    """Verifica si se puede conectar a la base de datos"""
    print("🔍 Probando conexión a PostgreSQL...")
    return db_manager.test_connection()


def create_database_structure():
    """Crea la estructura de la base de datos"""
    print("🏗️ Creando estructura de base de datos...")
    return db_manager.create_tables()


def create_carrera_desarrollo_software():
    """Crea la carrera 'Desarrollo de Software' si no existe"""
    db = db_manager.get_session()

    try:
        existing_carrera = (
            db.query(Carrera).filter(Carrera.nombre == "Desarrollo de Software").first()
        )

        if existing_carrera:
            print("✅ Carrera 'Desarrollo de Software' ya existe")
            return existing_carrera

        carrera_data = {
            "nombre": "Desarrollo de Software",
            "codigo": "DS",
            "descripcion": "Carrera técnica enfocada en el desarrollo de aplicaciones y sistemas de software",
            "duracion_ciclos": 6,
            "is_active": True,
        }

        new_carrera = Carrera(**carrera_data)
        db.add(new_carrera)
        db.commit()
        db.refresh(new_carrera)
        print("✅ Carrera 'Desarrollo de Software' creada")
        return new_carrera

    except Exception as e:
        db.rollback()
        print(f"❌ Error creando carrera: {e}")
        raise
    finally:
        db.close()


def create_test_users():
    """Crea un admin, un docente y un estudiante de prueba"""
    db = db_manager.get_session()

    try:
        carrera_ds = db.query(Carrera).filter(Carrera.codigo == "DS").first()

        # Solo 3 usuarios: 1 admin, 1 docente, 1 estudiante
        test_users = [
            {
                "dni": "12345678",
                "email": "admin@sistema.edu",
                "password": "admin123",
                "first_name": "Carlos",
                "last_name": "Administrador",
                "phone": "987654321",
                "role": RoleEnum.ADMIN,
            },
            {
                "dni": "87654321",
                "email": "docente@sistema.edu",
                "password": "docente123",
                "first_name": "María",
                "last_name": "Profesora",
                "phone": "987654322",
                "role": RoleEnum.DOCENTE,
                "especialidad": "Ingeniería de Software",
                "grado_academico": "Magíster",
                "fecha_ingreso": date(2020, 3, 1),
            },
            {
                "dni": "11223344",
                "email": "estudiante@sistema.edu",
                "password": "estudiante123",
                "first_name": "Pedro",
                "last_name": "López",
                "phone": "987654323",
                "role": RoleEnum.ESTUDIANTE,
            },
        ]

        created_count = 0
        skipped_count = 0

        for user_data in test_users:
            existing_user = (
                db.query(User)
                .filter(
                    (User.dni == user_data["dni"]) | (User.email == user_data["email"])
                )
                .first()
            )

            if existing_user:
                skipped_count += 1
                continue

            hashed_password = get_password_hash(user_data["password"])
            user_fields = {
                "dni": user_data["dni"],
                "email": user_data["email"],
                "password": hashed_password,
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "phone": user_data["phone"],
                "role": user_data["role"],
                "is_active": True,
            }

            if user_data["role"] == RoleEnum.ESTUDIANTE:
                user_fields.update(
                    {
                        "fecha_nacimiento": date(2000, 1, 1),
                        "direccion": "Av. Ejemplo 123, Lima",
                        "nombre_apoderado": "María López",
                        "telefono_apoderado": "987654324",
                        "carrera_id": carrera_ds.id if carrera_ds else None,
                    }
                )
            elif user_data["role"] == RoleEnum.DOCENTE:
                user_fields.update(
                    {
                        "especialidad": user_data.get("especialidad"),
                        "grado_academico": user_data.get("grado_academico"),
                        "fecha_ingreso": user_data.get("fecha_ingreso"),
                    }
                )

            new_user = User(**user_fields)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            created_count += 1

        print(
            f"👥 Usuarios de prueba -> creados: {created_count}, omitidos: {skipped_count}"
        )
        return created_count, skipped_count

    except Exception as e:
        db.rollback()
        print(f"❌ Error creando usuarios de prueba: {e}")
        raise
    finally:
        db.close()


def create_ciclos_2025():
    """Crea 6 ciclos (I a VI) para el año 2025 en la carrera DS"""
    db = db_manager.get_session()

    try:
        carrera_ds = db.query(Carrera).filter(Carrera.codigo == "DS").first()
        if not carrera_ds:
            print("❌ Error: No se encontró la carrera de Desarrollo de Software")
            return 0, 0

        ciclos_data = []
        for i in range(1, 7):  # Ciclos I al VI
            nombre_ciclo = ["", "I", "II", "III", "IV", "V", "VI"][i]
            ciclos_data.append(
                {
                    "nombre": nombre_ciclo,
                    "numero": i,
                    "año": 2025,
                    "fecha_inicio": date(2025, 3, 1),
                    "fecha_fin": date(2025, 7, 31),
                    "carrera_id": carrera_ds.id,
                    "is_active": True,
                }
            )

        created_count = 0
        skipped_count = 0

        for ciclo_data in ciclos_data:
            existing_ciclo = (
                db.query(Ciclo)
                .filter(
                    Ciclo.nombre == ciclo_data["nombre"],
                    Ciclo.año == ciclo_data["año"],
                    Ciclo.carrera_id == ciclo_data["carrera_id"],
                )
                .first()
            )

            if existing_ciclo:
                skipped_count += 1
                continue

            new_ciclo = Ciclo(**ciclo_data)
            db.add(new_ciclo)
            db.commit()
            db.refresh(new_ciclo)
            created_count += 1

        print(f"📚 Ciclos 2025 -> creados: {created_count}, omitidos: {skipped_count}")
        return created_count, skipped_count

    except Exception as e:
        db.rollback()
        print(f"❌ Error creando ciclos: {e}")
        raise
    finally:
        db.close()


def import_students_from_excel(sheet_name: str = "student"):
    """Importa estudiantes desde seeders/estudents.xlsx"""
    db = db_manager.get_session()

    try:
        file_path = Path(__file__).parent / "estudents.xlsx"
        if not file_path.exists():
            print("[Importación estudiantes] Archivo 'estudents.xlsx' no encontrado.")
            return 0, 0

        # Obtener carrera DS
        carrera_ds = db.query(Carrera).filter(Carrera.codigo == "DS").first()

        # Leer Excel con manejo robusto de codificación
        try:
            df_raw = pd.read_excel(
                file_path, sheet_name=sheet_name, header=None, engine="openpyxl"
            )
        except UnicodeDecodeError:
            try:
                df_raw = pd.read_excel(
                    file_path, sheet_name=sheet_name, header=None, engine="xlrd"
                )
            except:
                print("[Importación estudiantes] Error leyendo archivo Excel")
                return 0, 0

        # Detectar encabezados
        expected = {"dni", "correo", "email", "nombres", "apellidos", "ciclo"}
        best_idx = 0
        for i in range(min(5, len(df_raw))):
            row_vals = [
                str(v).strip().lower() for v in df_raw.iloc[i].tolist() if pd.notna(v)
            ]
            if any(exp in " ".join(row_vals) for exp in expected):
                best_idx = i
                break

        # Configurar DataFrame
        df = df_raw.iloc[best_idx + 1 :].copy()
        df.columns = [
            str(col).strip().lower() for col in df_raw.iloc[best_idx].tolist()
        ]

        created_count = 0
        skipped_count = 0

        print(f"[Importación estudiantes] Procesando {len(df)} registros...")

        for _, row in df.iterrows():
            try:
                # Extraer datos básicos
                dni = str(int(row.get("dni", 0))) if pd.notna(row.get("dni")) else ""
                email = str(row.get("correo", "")).strip()
                first_name = str(row.get("nombres", "")).strip()
                last_name = str(row.get("apellidos", "")).strip()

                # Validar campos requeridos
                if (
                    not dni
                    or len(dni) != 8
                    or not email
                    or not first_name
                    or not last_name
                ):
                    skipped_count += 1
                    continue

                # Verificar duplicados
                exists = (
                    db.query(User)
                    .filter((User.dni == dni) | (User.email == email))
                    .first()
                )

                if exists:
                    skipped_count += 1
                    continue

                # Crear usuario estudiante
                user_data = {
                    "dni": dni,
                    "email": email,
                    "password": get_password_hash(dni),  # Password = DNI
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": str(row.get("telefono", "")).strip() or "000000000",
                    "role": RoleEnum.ESTUDIANTE,
                    "fecha_nacimiento": date(2000, 1, 1),
                    "direccion": str(row.get("direccion", "")).strip() or "Lima, Perú",
                    "nombre_apoderado": str(row.get("nombre del apoderado", "")).strip()
                    or "Sin especificar",
                    "telefono_apoderado": "000000000",
                    "carrera_id": carrera_ds.id if carrera_ds else None,
                    "is_active": True,
                }

                new_user = User(**user_data)
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                created_count += 1

            except Exception as e:
                print(f"[Importación estudiantes] Error procesando fila: {e}")
                skipped_count += 1
                continue

        print(f"🎒 Estudiantes -> creados: {created_count}, omitidos: {skipped_count}")
        return created_count, skipped_count

    except Exception as e:
        db.rollback()
        print(f"❌ Error importando estudiantes: {e}")
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


def main():
    """Función principal del seeder"""
    try:
        print("🔄 Iniciando seeder PostgreSQL...")

        print("🔍 Verificando conexión a base de datos...")
        if not check_database_connection():
            raise Exception(
                "Error: no se puede conectar a la base de datos PostgreSQL."
            )
        print("✅ Conexión exitosa")

        print("🏗️ Creando estructura de base de datos...")
        if not create_database_structure():
            raise Exception(
                "Error: no se pudo crear la estructura de la base de datos."
            )
        print("✅ Estructura creada")

        print("🎓 Creando carrera de Desarrollo de Software...")
        create_carrera_desarrollo_software()

        print("📚 Creando ciclos 2025...")
        cc_created, cc_skipped = create_ciclos_2025()

        print("👥 Creando usuarios de prueba...")
        tu_created, tu_skipped = create_test_users()

        print("🎒 Importando estudiantes desde Excel...")
        st_created, st_skipped = import_students_from_excel("student")

        print("\n🎉 SEEDER COMPLETADO EXITOSAMENTE")
        print(f"📊 Resumen:")
        print(f"   • Ciclos 2025: {cc_created} creados, {cc_skipped} omitidos")
        print(f"   • Usuarios de prueba: {tu_created} creados, {tu_skipped} omitidos")
        print(f"   • Estudiantes: {st_created} creados, {st_skipped} omitidos")

        display_credentials()

    except Exception as e:
        import traceback

        print(f"❌ Error durante la ejecución del seeder: {str(e)}")
        print(f"🔍 Traceback completo:")
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
