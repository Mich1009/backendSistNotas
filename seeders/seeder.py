#!/usr/bin/env python3
"""
Seeder para poblar la base de datos con usuarios de prueba
Sistema de Notas Académico
"""
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from datetime import datetime, date
from app.database import SessionLocal, engine, Base
from app.shared.models import User, RoleEnum, Carrera, Ciclo, Matricula, Curso
from app.modules.auth.security import get_password_hash
from pathlib import Path
import pandas as pd
import re

def check_database_connection():
    """Verifica si se puede conectar a la base de datos"""
    try:
        # Intentar crear una conexión simple
        connection = engine.connect()
        connection.close()
        return True
    except OperationalError:
        return False

def create_database_structure():
    """Crea la estructura de la base de datos"""
    try:
        Base.metadata.create_all(bind=engine)
        return True
    except Exception:
        return False

def create_carrera_desarrollo_software():
    """Crea la carrera 'Desarrollo de Software' si no existe"""
    db: Session = SessionLocal()
    
    try:
        existing_carrera = db.query(Carrera).filter(
            Carrera.nombre == "Desarrollo de Software"
        ).first()
        
        if existing_carrera:
            return existing_carrera
        
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
        return new_carrera
        
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

def create_test_users():
    """Crea un admin, un docente y un estudiante de prueba"""
    db: Session = SessionLocal()
    
    try:
        carrera_ds = db.query(Carrera).filter(
            Carrera.codigo == "DS"
        ).first()
        
        # Solo 3 usuarios: 1 admin, 1 docente, 1 estudiante
        test_users = [
            {
                "dni": "12345678",
                "email": "admin@sistema.edu",
                "password": "admin123",
                "first_name": "Carlos",
                "last_name": "Administrador",
                "phone": "987654321",
                "role": RoleEnum.ADMIN
            },
            {
                "dni": "87654321",
                "email": "docente@sistema.edu",
                "password": "docente123",
                "first_name": "Juan",
                "last_name": "Pérez",
                "phone": "987654322",
                "role": RoleEnum.DOCENTE,
                "especialidad": "Ingeniería de Software",
                "grado_academico": "Magíster",
                "fecha_ingreso": date(2020, 3, 1)
            },
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
            existing_user = db.query(User).filter(
                (User.dni == user_data["dni"]) | (User.email == user_data["email"])
            ).first()
            
            if existing_user:
                skipped_count += 1
                continue
            
            hashed_password = get_password_hash(user_data["password"]) 
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
            
            if user_data["role"] == RoleEnum.ESTUDIANTE:
                user_fields.update({
                    "fecha_nacimiento": date(2000, 1, 1),
                    "direccion": "Av. Ejemplo 123, Lima",
                    "nombre_apoderado": "María López",
                    "telefono_apoderado": "987654324",
                    "carrera_id": carrera_ds.id if carrera_ds else None
                })
            elif user_data["role"] == RoleEnum.DOCENTE:
                user_fields.update({
                    "especialidad": user_data.get("especialidad"),
                    "grado_academico": user_data.get("grado_academico"),
                    "fecha_ingreso": user_data.get("fecha_ingreso")
                })
            
            new_user = User(**user_fields)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            created_count += 1
        
        return created_count, skipped_count
        
    except Exception as e:
        db.rollback()
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

def create_ciclos_2025():
    """Crea 6 ciclos (I a VI) para el año 2025 en la carrera DS"""
    db: Session = SessionLocal()
    try:
        carrera_ds = db.query(Carrera).filter(Carrera.codigo == "DS").first()
        if not carrera_ds:
            return 0, 0

        ciclos_2025 = [
            ("I", 1, date(2025, 4, 1), date(2025, 7, 31)),
            ("II", 2, date(2025, 9, 1), date(2025, 12, 31)),
            ("III", 3, date(2025, 4, 1), date(2025, 7, 31)),
            ("IV", 4, date(2025, 9, 1), date(2025, 12, 31)),
            ("V", 5, date(2025, 4, 1), date(2025, 7, 31)),
            ("VI", 6, date(2025, 9, 1), date(2025, 12, 15)),
        ]

        created_count = 0
        skipped_count = 0

        for nombre, numero, fecha_inicio, fecha_fin in ciclos_2025:
            existing = (
                db.query(Ciclo)
                .filter(
                    Ciclo.carrera_id == carrera_ds.id,
                    Ciclo.nombre == nombre,
                    Ciclo.fecha_inicio >= date(2025, 1, 1),
                    Ciclo.fecha_inicio <= date(2025, 12, 31),
                )
                .first()
            )
            if existing:
                skipped_count += 1
                continue

            new_ciclo = Ciclo(
                nombre=nombre,
                numero=numero,
                año=fecha_inicio.year,  # Calcular año automáticamente desde fecha_inicio
                descripcion=f"Ciclo {nombre} del año 2025",
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                carrera_id=carrera_ds.id,
                is_active=True,
            )
            db.add(new_ciclo)
            db.commit()
            db.refresh(new_ciclo)
            created_count += 1

        return created_count, skipped_count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def import_docentes_from_excel(sheet_name: str = "docentes"):
    """Importa docentes desde seeders/docentes_cursos.xlsx e inserta en users (Role=DOCENTE).
    - Password inicial: el mismo DNI
    - Omite si ya existe por DNI o email
    - Asigna valores por defecto para campos faltantes (especialidad, grado_academico, fecha_ingreso)
    """
    db: Session = SessionLocal()
    try:
        file_path = Path(__file__).parent / "docentes_cursos.xlsx"
        if not file_path.exists():
            print("[Importación docentes] Archivo 'docentes_cursos.xlsx' no encontrado.")
            return 0, 0

        # Mostrar hojas disponibles para ayudar a diagnóstico
        try:
            xls = pd.ExcelFile(file_path)
            print(f"[Importación docentes] Hojas disponibles: {xls.sheet_names}")
        except Exception:
            xls = None

        # Leer sin encabezado para detectar la fila de encabezados real
        try:
            df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        except ValueError:
            df_raw = pd.read_excel(file_path, header=None)
            print("[Importación docentes] Hoja 'docentes' no encontrada, se usó la primera hoja.")

        # Normalizar encabezados (minúsculas, sin acentos)
        def _normalize_col(col: str) -> str:
            s = str(col).strip().lower()
            s = (
                s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
                 .replace("Á", "a").replace("É", "e").replace("Í", "i").replace("Ó", "o").replace("Ú", "u")
                 .replace("ñ", "n").replace("Ñ", "n")
            )
            return s

        # Detectar fila de encabezados buscando coincidencias con claves esperadas
        expected = {"dni", "correo", "email", "nombre", "apellidos", "celular", "grado academico", "grado_academico", "especialidad", "rol"}
        best_idx = 0
        best_score = -1
        best_header = None
        max_rows_check = min(10, len(df_raw))
        for i in range(max_rows_check):
            row_vals = ["" if pd.isna(v) else str(v) for v in df_raw.iloc[i].tolist()]
            norm_row = [_normalize_col(v) for v in row_vals]
            score = sum(1 for v in norm_row if v in expected)
            if score > best_score:
                best_score = score
                best_idx = i
                best_header = norm_row

        if best_header is None:
            best_header = [_normalize_col(c) for c in df_raw.iloc[0].tolist()]
            best_idx = 0

        print(f"[Importación docentes] Encabezado detectado en fila {best_idx}: {best_header}")

        # Construir DataFrame con encabezados detectados y eliminar columnas vacías/unnamed
        df = df_raw.iloc[best_idx + 1:].copy()
        df.columns = best_header
        df = df.loc[:, [c for c in df.columns if c and not c.startswith("unnamed")]]
        print(f"[Importación docentes] Columnas normalizadas: {list(df.columns)}")

        created = 0
        skipped = 0
        missing_required = 0
        duplicates = 0
        exceptions = 0

        def _sanitize_dni(value) -> str:
            """Convierte el DNI a string de 8 dígitos (remueve no-dígitos y .0 de floats)."""
            if value is None or (isinstance(value, float) and pd.isna(value)):
                return ""
            s = str(value).strip()
            # eliminar parte decimal si viene como 12345678.0
            if s.endswith(".0"):
                s = s[:-2]
            # remover no dígitos
            import re as _re
            s = _re.sub(r"\D", "", s)
            # si tiene más de 8 dígitos, tomar los primeros 8
            if len(s) >= 8:
                s = s[:8]
            return s

        for _, row in df.iterrows():
            try:
                dni = _sanitize_dni(row.get("dni"))
                email = row.get("correo") or row.get("email")
                if pd.isna(email) or str(email).strip() == "":
                    email = None
                first_name = row.get("nombre")
                last_name = row.get("apellidos")

                phone_raw = row.get("celular")
                phone = None
                if pd.notna(phone_raw):
                    phone = str(phone_raw).strip()

                especialidad = row.get("especialidad")
                if especialidad is None or (isinstance(especialidad, float) and pd.isna(especialidad)) or str(especialidad).strip() == "":
                    especialidad = "No especificado"

                grado_academico = row.get("grado academico") or row.get("grado_academico")
                if grado_academico is None or (isinstance(grado_academico, float) and pd.isna(grado_academico)) or str(grado_academico).strip() == "":
                    grado_academico = "No especificado"

                fecha_ingreso = date.today()

                # Validar requeridos
                if not dni or len(dni) != 8 or not email or not first_name or not last_name:
                    missing_required += 1
                    skipped += 1
                    continue

                # Verificar duplicados
                exists = db.query(User).filter((User.dni == dni) | (User.email == email)).first()
                if exists:
                    duplicates += 1
                    skipped += 1
                    continue

                # Password por defecto: DNI
                hashed_password = get_password_hash(dni)

                new_user = User(
                    dni=dni,
                    email=email,
                    hashed_password=hashed_password,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    role=RoleEnum.DOCENTE,
                    especialidad=especialidad,
                    grado_academico=grado_academico,
                    fecha_ingreso=fecha_ingreso,
                    is_active=True,
                )
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                created += 1
            except Exception as ex:
                print(f"[Importación docentes] Error en fila: {ex}")
                db.rollback()
                exceptions += 1
                skipped += 1
                continue

        print(
            f"[Importación docentes] Resumen -> creados: {created}, omitidos: {skipped} | "
            f"faltan requeridos: {missing_required}, duplicados: {duplicates}, errores: {exceptions}"
        )
        return created, skipped
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def generate_matricula_code(db: Session) -> str:
    """Genera el siguiente código de matrícula con formato MTC-0001, MTC-0002, etc."""
    # Buscar el último código de matrícula existente
    last_matricula = db.query(Matricula).filter(
        Matricula.codigo_matricula.like("MTC-%")
    ).order_by(Matricula.codigo_matricula.desc()).first()
    
    if last_matricula and last_matricula.codigo_matricula:
        # Extraer el número del último código (ej: MTC-0001 -> 1)
        try:
            last_number = int(last_matricula.codigo_matricula.split("-")[1])
            next_number = last_number + 1
        except (IndexError, ValueError):
            next_number = 1
    else:
        next_number = 1
    
    # Formatear con 4 dígitos: MTC-0001, MTC-0002, etc.
    return f"MTC-{next_number:04d}"

def import_students_from_excel(sheet_name: str = "student"):
    """Importa estudiantes desde seeders/estudents.xlsx e inserta en users (Role=ESTUDIANTE).
    - Password inicial: el mismo DNI
    - Omite si ya existe por DNI o email
    - Asocia a la carrera DS si existe
    """
    db: Session = SessionLocal()
    try:
        # Asegurar carrera DS
        carrera_ds = db.query(Carrera).filter(Carrera.codigo == "DS").first()
        if not carrera_ds:
            carrera_ds = create_carrera_desarrollo_software()

        file_path = Path(__file__).parent / "estudents.xlsx"
        if not file_path.exists():
            print("[Importación estudiantes] Archivo 'estudents.xlsx' no encontrado.")
            return 0, 0

        # Mostrar hojas disponibles para ayudar a diagnóstico
        try:
            xls = pd.ExcelFile(file_path)
            print(f"[Importación estudiantes] Hojas disponibles: {xls.sheet_names}")
        except Exception:
            xls = None

        # Leer sin encabezado para detectar la fila de encabezados real
        try:
            df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        except ValueError:
            df_raw = pd.read_excel(file_path, header=None)
            print("[Importación estudiantes] Hoja 'student' no encontrada, se usó la primera hoja.")

        # Normalizar encabezados (minúsculas, sin acentos)
        def _normalize_col(col: str) -> str:
            s = str(col).strip().lower()
            s = (
                s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
                 .replace("Á", "a").replace("É", "e").replace("Í", "i").replace("Ó", "o").replace("Ú", "u")
                 .replace("ñ", "n").replace("Ñ", "n")
            )
            return s

        # Detectar fila de encabezados buscando coincidencias con claves esperadas
        expected = {"dni", "correo", "email", "nombres", "apellidos", "direccion", "nombre del apoderado", "fecha de nacimiento", "carrera", "telefono", "teléfono", "ciclo"}
        best_idx = 0
        best_score = -1
        best_header = None
        max_rows_check = min(10, len(df_raw))
        for i in range(max_rows_check):
            row_vals = ["" if pd.isna(v) else str(v) for v in df_raw.iloc[i].tolist()]
            norm_row = [_normalize_col(v) for v in row_vals]
            score = sum(1 for v in norm_row if v in expected)
            if score > best_score:
                best_score = score
                best_idx = i
                best_header = norm_row

        if best_header is None:
            best_header = [_normalize_col(c) for c in df_raw.iloc[0].tolist()]
            best_idx = 0

        print(f"[Importación estudiantes] Encabezado detectado en fila {best_idx}: {best_header}")

        # Construir DataFrame con encabezados detectados y eliminar columnas vacías/unnamed
        df = df_raw.iloc[best_idx + 1:].copy()
        df.columns = best_header
        df = df.loc[:, [c for c in df.columns if c and not c.startswith("unnamed")]]
        print(f"[Importación estudiantes] Columnas normalizadas: {list(df.columns)}")

        # Detectar columnas de teléfono (alumno y apoderado)
        telefono_cols = [c for c in df.columns if "telefono" in c]
        alumno_phone_col = telefono_cols[0] if len(telefono_cols) >= 1 else None
        apoderado_phone_col = telefono_cols[1] if len(telefono_cols) >= 2 else None

        created = 0
        skipped = 0
        missing_required = 0
        duplicates = 0
        exceptions = 0
        matriculas_created = 0

        def _sanitize_dni(value) -> str:
            """Convierte el DNI a string de 8 dígitos (remueve no-dígitos y .0 de floats)."""
            if value is None or (isinstance(value, float) and pd.isna(value)):
                return ""
            s = str(value).strip()
            # eliminar parte decimal si viene como 12345678.0
            if s.endswith(".0"):
                s = s[:-2]
            # remover no dígitos
            import re as _re
            s = _re.sub(r"\D", "", s)
            # si tiene más de 8 dígitos, tomar los primeros 8
            if len(s) >= 8:
                s = s[:8]
            return s

        def _clean_str(val) -> str:
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return ""
            s = str(val).strip()
            return "" if s.lower() in {"nan", "none", "null"} else s

        def _get_ciclo_number(ciclo_str: str) -> int:
            """Convierte ciclo romano (I, II, III, etc.) a número entero"""
            if not ciclo_str:
                return 0
            ciclo_str = ciclo_str.strip().upper()
            roman_to_int = {
                'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6,
                '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6
            }
            return roman_to_int.get(ciclo_str, 0)

        def _create_enrollments_up_to_cycle(estudiante_id: int, max_ciclo_num: int, carrera_id: int) -> int:
            """Crea matrículas desde el ciclo I hasta el ciclo actual del estudiante"""
            enrollments_created = 0
            try:
                # Obtener todos los ciclos de la carrera ordenados por número
                ciclos = db.query(Ciclo).filter(
                    Ciclo.carrera_id == carrera_id,
                    Ciclo.is_active == True
                ).order_by(Ciclo.numero).all()
                
                # Crear matrículas para cada ciclo hasta el máximo
                for ciclo in ciclos:
                    if ciclo.numero <= max_ciclo_num:
                        # Verificar si ya existe la matrícula
                        existing_matricula = db.query(Matricula).filter(
                            Matricula.estudiante_id == estudiante_id,
                            Matricula.ciclo_id == ciclo.id
                        ).first()
                        
                        if not existing_matricula:
                            # Generar código de matrícula automático
                            codigo_matricula = generate_matricula_code(db)
                            
                            nueva_matricula = Matricula(
                                estudiante_id=estudiante_id,
                                ciclo_id=ciclo.id,
                                codigo_matricula=codigo_matricula,
                                fecha_matricula=date.today(),
                                estado="activa",
                                is_active=True
                            )
                            db.add(nueva_matricula)
                            db.commit()  # Commit inmediato para asegurar secuencia
                            enrollments_created += 1
                
                return enrollments_created
            except Exception as e:
                print(f"[Matriculas] Error creando matrículas para estudiante {estudiante_id}: {e}")
                return 0

        # Comprobar primeras filas para diagnóstico
        if len(df) > 0:
            sample = df.head(5).to_dict(orient="records")
            print("[Importación estudiantes] Muestra (5 filas):")
            for r in sample:
                print({k: r.get(k) for k in ["dni", "correo", "email", "nombres", "apellidos"]})

        for _, row in df.iterrows():
            try:
                dni = _sanitize_dni(row.get("dni"))
                email = _clean_str(row.get("correo") or row.get("email"))
                first_name = _clean_str(row.get("nombres"))
                last_name = _clean_str(row.get("apellidos"))
                direccion = _clean_str(row.get("direccion"))
                nombre_apoderado = _clean_str(row.get("nombre del apoderado") or row.get("nombre_apoderado"))

                # Carrera opcional desde Excel (por código o nombre)
                carrera_val = _clean_str(row.get("carrera"))
                carrera_id = carrera_ds.id if carrera_ds else None
                if carrera_val:
                    c = db.query(Carrera).filter((Carrera.codigo == carrera_val) | (Carrera.nombre == carrera_val)).first()
                    if c:
                        carrera_id = c.id

                phone = _clean_str(row.get(alumno_phone_col)) if alumno_phone_col else None
                telefono_apoderado = _clean_str(row.get(apoderado_phone_col)) if apoderado_phone_col else None

                # Obtener ciclo actual del estudiante
                ciclo_actual_str = _clean_str(row.get("ciclo"))
                ciclo_actual_num = _get_ciclo_number(ciclo_actual_str)

                # Fecha de nacimiento: dd/mm/yyyy
                fn_raw = row.get("fecha de nacimiento") or row.get("fecha_nacimiento")
                fecha_nacimiento = None
                if pd.notna(fn_raw):
                    fn = pd.to_datetime(fn_raw, dayfirst=True, errors="coerce")
                    if pd.notna(fn):
                        fecha_nacimiento = fn.date()

                if not dni or len(dni) != 8 or not email or not first_name or not last_name:
                    missing_required += 1
                    skipped += 1
                    continue

                # Verificar duplicados
                exists = db.query(User).filter((User.dni == dni) | (User.email == email)).first()
                if exists:
                    duplicates += 1
                    skipped += 1
                    continue

                # Password por defecto: DNI
                hashed_password = get_password_hash(dni)

                new_user = User(
                    dni=dni,
                    email=email,
                    hashed_password=hashed_password,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    role=RoleEnum.ESTUDIANTE,
                    fecha_nacimiento=fecha_nacimiento,
                    direccion=direccion,
                    nombre_apoderado=nombre_apoderado,
                    telefono_apoderado=telefono_apoderado,
                    carrera_id=carrera_id,
                    is_active=True,
                )
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                created += 1

                # Crear matrículas desde ciclo I hasta el ciclo actual
                if ciclo_actual_num > 0 and carrera_id:
                    enrollments = _create_enrollments_up_to_cycle(new_user.id, ciclo_actual_num, carrera_id)
                    matriculas_created += enrollments
                    if enrollments > 0:
                        db.commit()  # Confirmar las matrículas creadas

            except Exception as ex:
                print(f"[Importación estudiantes] Error en fila: {ex}")
                db.rollback()
                exceptions += 1
                skipped += 1
                continue

        print(
            f"[Importación estudiantes] Resumen -> creados: {created}, omitidos: {skipped}, matrículas: {matriculas_created} | "
            f"faltan requeridos: {missing_required}, duplicados: {duplicates}, errores: {exceptions}"
        )
        return created, skipped
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def import_courses_from_excel(sheet_name: str = "cursos"):
    """Importa cursos desde seeders/docentes_cursos.xlsx e inserta en cursos.
    - Relaciona con ciclo basado en nombre del ciclo (romano) y año
    - Relaciona con docente basado en DNI
    - Omite si ya existe un curso con el mismo nombre en el mismo ciclo
    """
    db: Session = SessionLocal()
    try:
        # Asegurar carrera DS
        carrera_ds = db.query(Carrera).filter(Carrera.codigo == "DS").first()
        if not carrera_ds:
            carrera_ds = create_carrera_desarrollo_software()

        file_path = Path(__file__).parent / "docentes_cursos.xlsx"
        if not file_path.exists():
            print("[Importación cursos] Archivo 'docentes_cursos.xlsx' no encontrado.")
            return 0, 0

        # Mostrar hojas disponibles para ayudar a diagnóstico
        try:
            xls = pd.ExcelFile(file_path)
            print(f"[Importación cursos] Hojas disponibles: {xls.sheet_names}")
        except Exception:
            xls = None

        # Leer sin encabezado para detectar la fila de encabezados real
        try:
            df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        except ValueError:
            df_raw = pd.read_excel(file_path, header=None)
            print("[Importación cursos] Hoja 'cursos' no encontrada, se usó la primera hoja.")

        # Normalizar encabezados (minúsculas, sin acentos)
        def _normalize_col(col: str) -> str:
            s = str(col).strip().lower()
            s = (
                s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
                 .replace("Á", "a").replace("É", "e").replace("Í", "i").replace("Ó", "o").replace("Ú", "u")
                 .replace("ñ", "n").replace("Ñ", "n")
            )
            return s

        # Detectar fila de encabezados buscando coincidencias con claves esperadas
        expected = {"cursos", "curso", "nombre", "ciclos", "ciclo", "docente", "dni", "año", "ano"}
        best_idx = 0
        best_score = -1
        best_header = None
        max_rows_check = min(10, len(df_raw))
        for i in range(max_rows_check):
            row_vals = ["" if pd.isna(v) else str(v) for v in df_raw.iloc[i].tolist()]
            norm_row = [_normalize_col(v) for v in row_vals]
            score = sum(1 for v in norm_row if v in expected)
            if score > best_score:
                best_score = score
                best_idx = i
                best_header = norm_row

        if best_header is None:
            best_header = [_normalize_col(c) for c in df_raw.iloc[0].tolist()]
            best_idx = 0

        print(f"[Importación cursos] Encabezado detectado en fila {best_idx}: {best_header}")

        # Construir DataFrame con encabezados detectados y eliminar columnas vacías/unnamed
        df = df_raw.iloc[best_idx + 1:].copy()
        df.columns = best_header
        df = df.loc[:, [c for c in df.columns if c and not c.startswith("unnamed")]]
        print(f"[Importación cursos] Columnas normalizadas: {list(df.columns)}")

        created = 0
        skipped = 0
        missing_required = 0
        duplicates = 0
        exceptions = 0

        def _sanitize_dni(value) -> str:
            """Convierte el DNI a string de 8 dígitos (remueve no-dígitos y .0 de floats)."""
            if value is None or (isinstance(value, float) and pd.isna(value)):
                return ""
            s = str(value).strip()
            # eliminar parte decimal si viene como 12345678.0
            if s.endswith(".0"):
                s = s[:-2]
            # remover no dígitos
            import re as _re
            s = _re.sub(r"\D", "", s)
            # si tiene más de 8 dígitos, tomar los primeros 8
            if len(s) >= 8:
                s = s[:8]
            return s

        def _clean_str(val) -> str:
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return ""
            s = str(val).strip()
            return "" if s.lower() in {"nan", "none", "null"} else s

        def _convert_roman_to_int(roman: str) -> int:
            """Convierte números romanos a enteros"""
            if not roman:
                return 0
            roman = roman.strip().upper()
            roman_to_int = {
                'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6,
                'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
            }
            return roman_to_int.get(roman, 0)

        for _, row in df.iterrows():
            try:
                nombre_curso = _clean_str(row.get("cursos"))
                ciclo_romano = _clean_str(row.get("ciclos"))
                docente_dni = _sanitize_dni(row.get("docente"))
                año = row.get("año") or row.get("ano")
                
                if pd.notna(año):
                    año = int(año)
                else:
                    año = 2025  # Valor por defecto

                # Validar requeridos
                if not nombre_curso or not ciclo_romano:
                    missing_required += 1
                    skipped += 1
                    continue

                # Buscar el ciclo correspondiente
                ciclo_numero = _convert_roman_to_int(ciclo_romano)
                if ciclo_numero == 0:
                    print(f"[Importación cursos] Ciclo romano inválido: {ciclo_romano}")
                    missing_required += 1
                    skipped += 1
                    continue

                ciclo = db.query(Ciclo).filter(
                    Ciclo.carrera_id == carrera_ds.id,
                    Ciclo.nombre == ciclo_romano,
                    Ciclo.año == año
                ).first()

                if not ciclo:
                    print(f"[Importación cursos] Ciclo no encontrado: {ciclo_romano} del año {año}")
                    missing_required += 1
                    skipped += 1
                    continue

                # Buscar docente por DNI (opcional)
                docente = None
                if docente_dni:
                    docente = db.query(User).filter(
                        User.dni == docente_dni,
                        User.role == RoleEnum.DOCENTE
                    ).first()
                    if not docente:
                        print(f"[Importación cursos] Docente no encontrado con DNI: {docente_dni}")

                # Generar código único para el curso
                # Formato: DS-I-001, DS-II-002, etc.
                # Verificar si ya existe el curso
                existing_curso = db.query(Curso).filter(
                    Curso.nombre == nombre_curso,
                    Curso.ciclo_id == ciclo.id
                ).first()

                if existing_curso:
                    duplicates += 1
                    skipped += 1
                    continue

                # Crear el curso
                new_curso = Curso(
                    nombre=nombre_curso,
                    descripcion=f"Curso del ciclo {ciclo_romano} - {año}",
                    ciclo_id=ciclo.id,
                    docente_id=docente.id if docente else None,
                    is_active=True
                )
                
                db.add(new_curso)
                db.commit()
                db.refresh(new_curso)
                created += 1

            except Exception as ex:
                print(f"[Importación cursos] Error en fila: {ex}")
                db.rollback()
                exceptions += 1
                skipped += 1
                continue

        print(
            f"[Importación cursos] Resumen -> creados: {created}, omitidos: {skipped} | "
            f"faltan requeridos: {missing_required}, duplicados: {duplicates}, errores: {exceptions}"
        )
        return created, skipped
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    try:
        if not check_database_connection():
            raise Exception("Error: no se puede conectar a la base de datos.")
        if not create_database_structure():
            raise Exception("Error: no se pudo crear la estructura de la base de datos.")

        create_carrera_desarrollo_software()
        cc_created, cc_skipped = create_ciclos_2025()
        tu_created, tu_skipped = create_test_users()
        st_created, st_skipped = import_students_from_excel("student")
        dc_created, dc_skipped = import_docentes_from_excel("docentes")
        cr_created, cr_skipped = import_courses_from_excel("cursos")
        print(f"Ciclos 2025 -> creados: {cc_created}, omitidos: {cc_skipped}")
        print(f"Usuarios de prueba -> creados: {tu_created}, omitidos: {tu_skipped}")
        print(f"Estudiantes (Excel) -> creados: {st_created}, omitidos: {st_skipped}")
        print(f"Docentes (Excel) -> creados: {dc_created}, omitidos: {dc_skipped}")
        print(f"Cursos (Excel) -> creados: {cr_created}, omitidos: {cr_skipped}")
        print("Éxito: seeder completado.")
    except Exception as e:
        print(str(e))