"""
Script para crear datos de prueba en el sistema de notas
Ejecutar: python create_test_data.py
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.shared.models import User, RoleEnum, Carrera, Ciclo, Curso, Matricula, Nota
from app.auth.security import get_password_hash
from datetime import date, datetime
from decimal import Decimal
import os

# Configuración de la base de datos
DATABASE_URL = "sqlite:///./sistema_notas.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_test_data():
    db = SessionLocal()

    try:
        print("🔧 Creando datos de prueba...")

        # 1. Crear carreras de prueba
        carrera1 = Carrera(
            nombre="Ingeniería de Sistemas",
            codigo="ING_SIS",
            descripcion="Carrera de Ingeniería de Sistemas",
            duracion_ciclos=10,
            is_active=True,
        )

        carrera2 = Carrera(
            nombre="Administración",
            codigo="ADM",
            descripcion="Carrera de Administración de Empresas",
            duracion_ciclos=8,
            is_active=True,
        )

        db.add_all([carrera1, carrera2])
        db.commit()
        print("✅ Carreras creadas")

        # 2. Crear ciclos de prueba
        ciclo1 = Ciclo(
            nombre="Ciclo I",
            numero=1,
            año=2024,
            descripcion="Primer ciclo académico",
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 7, 31),
            carrera_id=carrera1.id,
            is_active=True,
        )

        ciclo2 = Ciclo(
            nombre="Ciclo II",
            numero=2,
            año=2024,
            descripcion="Segundo ciclo académico",
            fecha_inicio=date(2024, 8, 1),
            fecha_fin=date(2024, 12, 31),
            carrera_id=carrera1.id,
            is_active=True,
        )

        ciclo3 = Ciclo(
            nombre="Ciclo III",
            numero=3,
            año=2024,
            descripcion="Tercer ciclo académico",
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 7, 31),
            carrera_id=carrera1.id,
            is_active=True,
        )

        db.add_all([ciclo1, ciclo2, ciclo3])
        db.commit()
        print("✅ Ciclos creados")

        # 3. Crear usuarios de prueba

        # Profesor de prueba
        profesor = User(
            dni="12345678",
            email="profesor@test.com",
            hashed_password=get_password_hash("123456"),
            first_name="Juan",
            last_name="Profesor",
            phone="987654321",
            role=RoleEnum.DOCENTE,
            especialidad="Matemáticas",
            grado_academico="Magister",
            fecha_ingreso=date(2020, 1, 15),
            is_active=True,
        )

        # Admin de prueba
        admin = User(
            dni="87654321",
            email="admin@test.com",
            hashed_password=get_password_hash("123456"),
            first_name="María",
            last_name="Administradora",
            role=RoleEnum.ADMIN,
            is_active=True,
        )

        db.add_all([profesor, admin])
        db.commit()
        print("✅ Usuarios (profesor y admin) creados")

        # 4. Crear estudiantes de prueba
        estudiantes = []
        nombres = [
            ("Ana", "García"),
            ("Carlos", "López"),
            ("María", "Rodríguez"),
            ("José", "Martínez"),
            ("Sofía", "Hernández"),
            ("Diego", "González"),
            ("Lucia", "Pérez"),
            ("Miguel", "Sánchez"),
            ("Valentina", "Ramírez"),
            ("Andrés", "Torres"),
            ("Isabella", "Flores"),
            ("Sebastián", "Rivera"),
        ]

        for i, (nombre, apellido) in enumerate(nombres, 1):
            estudiante = User(
                dni=f"1000000{i:02d}",
                email=f"estudiante{i}@test.com",
                hashed_password=get_password_hash("123456"),
                first_name=nombre,
                last_name=apellido,
                role=RoleEnum.ESTUDIANTE,
                fecha_nacimiento=date(2000 + (i % 5), (i % 12) + 1, (i % 28) + 1),
                direccion=f"Dirección {i}, Lima",
                carrera_id=carrera1.id,
                is_active=True,
            )
            estudiantes.append(estudiante)

        db.add_all(estudiantes)
        db.commit()
        print(f"✅ {len(estudiantes)} estudiantes creados")

        # 5. Crear cursos de prueba
        cursos = [
            Curso(
                nombre="Matemáticas I",
                descripcion="Fundamentos de matemáticas",
                ciclo_id=ciclo1.id,
                docente_id=profesor.id,
                is_active=True,
            ),
            Curso(
                nombre="Programación Básica",
                descripcion="Introducción a la programación",
                ciclo_id=ciclo1.id,
                docente_id=profesor.id,
                is_active=True,
            ),
            Curso(
                nombre="Matemáticas II",
                descripcion="Cálculo diferencial",
                ciclo_id=ciclo2.id,
                docente_id=profesor.id,
                is_active=True,
            ),
            Curso(
                nombre="Algoritmos",
                descripcion="Estructuras de datos y algoritmos",
                ciclo_id=ciclo2.id,
                docente_id=profesor.id,
                is_active=True,
            ),
            Curso(
                nombre="Base de Datos",
                descripcion="Diseño y administración de base de datos",
                ciclo_id=ciclo3.id,
                docente_id=profesor.id,
                is_active=True,
            ),
        ]

        db.add_all(cursos)
        db.commit()
        print(f"✅ {len(cursos)} cursos creados")

        # 6. Crear matrículas de prueba
        matriculas = []
        for estudiante in estudiantes:
            # Matricular en ciclo 1 (todos)
            matricula1 = Matricula(
                estudiante_id=estudiante.id,
                ciclo_id=ciclo1.id,
                codigo_matricula=f"MAT2024-1-{estudiante.dni}",
                fecha_matricula=date(2024, 2, 15),
                estado="activa",
                is_active=True,
            )
            matriculas.append(matricula1)

            # Algunos en ciclo 2
            if estudiante.id % 2 == 0:
                matricula2 = Matricula(
                    estudiante_id=estudiante.id,
                    ciclo_id=ciclo2.id,
                    codigo_matricula=f"MAT2024-2-{estudiante.dni}",
                    fecha_matricula=date(2024, 7, 15),
                    estado="activa",
                    is_active=True,
                )
                matriculas.append(matricula2)

            # Pocos en ciclo 3
            if estudiante.id % 3 == 0:
                matricula3 = Matricula(
                    estudiante_id=estudiante.id,
                    ciclo_id=ciclo3.id,
                    codigo_matricula=f"MAT2024-3-{estudiante.dni}",
                    fecha_matricula=date(2024, 2, 15),
                    estado="activa",
                    is_active=True,
                )
                matriculas.append(matricula3)

        db.add_all(matriculas)
        db.commit()
        print(f"✅ {len(matriculas)} matrículas creadas")

        # 7. Crear notas de prueba
        notas = []
        import random

        for curso in cursos:
            # Obtener estudiantes matriculados en el ciclo de este curso
            estudiantes_ciclo = (
                db.query(User)
                .join(Matricula, User.id == Matricula.estudiante_id)
                .filter(
                    Matricula.ciclo_id == curso.ciclo_id,
                    Matricula.is_active == True,
                    User.role == RoleEnum.ESTUDIANTE,
                )
                .all()
            )

            for estudiante in estudiantes_ciclo:
                # Generar notas aleatorias pero realistas
                nota = Nota(
                    estudiante_id=estudiante.id,
                    curso_id=curso.id,
                    tipo_evaluacion="EVALUACION",
                    peso=Decimal("1.0"),
                    fecha_evaluacion=date(2024, 5, 15),
                    observaciones="Notas de prueba",
                )

                # Evaluaciones (1-8)
                for i in range(1, 9):
                    if random.random() > 0.3:  # 70% probabilidad de tener nota
                        nota_valor = round(random.uniform(8, 18), 2)
                        setattr(nota, f"evaluacion{i}", Decimal(str(nota_valor)))

                # Prácticas (1-4)
                for i in range(1, 5):
                    if random.random() > 0.2:  # 80% probabilidad de tener nota
                        nota_valor = round(random.uniform(10, 19), 2)
                        setattr(nota, f"practica{i}", Decimal(str(nota_valor)))

                # Parciales (1-2)
                for i in range(1, 3):
                    if random.random() > 0.1:  # 90% probabilidad de tener nota
                        nota_valor = round(random.uniform(9, 17), 2)
                        setattr(nota, f"parcial{i}", Decimal(str(nota_valor)))

                # Calcular promedio final (simple)
                notas_values = []
                for i in range(1, 9):
                    val = getattr(nota, f"evaluacion{i}")
                    if val:
                        notas_values.append(float(val))
                for i in range(1, 5):
                    val = getattr(nota, f"practica{i}")
                    if val:
                        notas_values.append(float(val))
                for i in range(1, 3):
                    val = getattr(nota, f"parcial{i}")
                    if val:
                        notas_values.append(float(val))

                if notas_values:
                    promedio = sum(notas_values) / len(notas_values)
                    nota.promedio_final = Decimal(str(round(promedio, 2)))
                    nota.estado = "APROBADO" if promedio >= 11 else "DESAPROBADO"

                notas.append(nota)

        db.add_all(notas)
        db.commit()
        print(f"✅ {len(notas)} notas de prueba creadas")

        # Resumen final
        print("\n" + "=" * 50)
        print("📊 RESUMEN DE DATOS CREADOS:")
        print("=" * 50)
        print(f"👤 Profesor: profesor@test.com (pass: 123456)")
        print(f"👤 Admin: admin@test.com (pass: 123456)")
        print(
            f"🎓 Estudiantes: {len(estudiantes)} (estudiante1@test.com, etc. - pass: 123456)"
        )
        print(f"🏫 Carreras: {len([carrera1, carrera2])}")
        print(f"📚 Ciclos: {len([ciclo1, ciclo2, ciclo3])}")
        print(f"📖 Cursos: {len(cursos)}")
        print(f"📝 Matrículas: {len(matriculas)}")
        print(f"📊 Notas: {len(notas)}")
        print("=" * 50)
        print("✅ ¡Datos de prueba creados exitosamente!")
        print("✅ Ahora puedes iniciar sesión como profesor y ver tus cursos")

    except Exception as e:
        print(f"❌ Error creando datos de prueba: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_test_data()
