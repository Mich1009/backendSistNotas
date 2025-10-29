#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.shared.models import Carrera, Ciclo


def ensure_db_structure():
    Base.metadata.create_all(bind=engine)


def ensure_carrera_ds(db: Session) -> Carrera:
    carrera = db.query(Carrera).filter(Carrera.codigo == "DS").first()
    if carrera:
        return carrera
    carrera = Carrera(
        nombre="Desarrollo de Software",
        codigo="DS",
        descripcion="Carrera técnica enfocada en el desarrollo de aplicaciones y sistemas de software",
        duracion_ciclos=6,
        is_active=True,
    )
    db.add(carrera)
    db.commit()
    db.refresh(carrera)
    return carrera


def create_ciclos_multi_years(db: Session, carrera: Carrera, years: list[int]):
    created = 0
    skipped = 0
    for year in years:
        ciclos = [
            ("I", 1, date(year, 4, 1), date(year, 7, 31)),
            ("II", 2, date(year, 9, 1), date(year, 12, 31)),
            ("III", 3, date(year, 4, 1), date(year, 7, 31)),
            ("IV", 4, date(year, 9, 1), date(year, 12, 31)),
            ("V", 5, date(year, 4, 1), date(year, 7, 31)),
            ("VI", 6, date(year, 9, 1), date(year, 12, 15)),
        ]
        for nombre, numero, f_ini, f_fin in ciclos:
            exists = (
                db.query(Ciclo)
                .filter(
                    Ciclo.carrera_id == carrera.id,
                    Ciclo.nombre == nombre,
                    Ciclo.año == year,
                )
                .first()
            )
            if exists:
                skipped += 1
                continue
            c = Ciclo(
                nombre=nombre,
                numero=numero,
                año=year,
                descripcion=f"Ciclo {nombre} del año {year}",
                fecha_inicio=f_ini,
                fecha_fin=f_fin,
                carrera_id=carrera.id,
                is_active=True,
            )
            db.add(c)
            db.commit()
            created += 1
    return created, skipped


if __name__ == "__main__":
    print("🔄 Creando ciclos multi-año (2023, 2024, 2025) ...")
    ensure_db_structure()
    db = SessionLocal()
    try:
        carrera = ensure_carrera_ds(db)
        created, skipped = create_ciclos_multi_years(db, carrera, [2023, 2024, 2025])
        print(f"✅ Listo. Ciclos creados: {created}, omitidos: {skipped}")
    finally:
        db.close()