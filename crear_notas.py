#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.shared.models import User, Curso, Nota
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date

def crear_notas_prueba():
    # Obtener sesión de base de datos
    db = next(get_db())
    
    try:
        # Buscar el estudiante
        estudiante = db.query(User).filter(User.dni == '11223344').first()
        if not estudiante:
            print('Estudiante no encontrado')
            return False
        
        print(f'Estudiante encontrado: {estudiante.first_name} {estudiante.last_name}')
        
        # Obtener cursos del ciclo I
        cursos = db.query(Curso).filter(Curso.ciclo_id == 1, Curso.is_active == True).all()
        print(f'Cursos encontrados: {len(cursos)}')
        
        # Crear notas para cada curso
        notas_creadas = 0
        for curso in cursos:
            # Verificar si ya existe una nota para este estudiante y curso
            nota_existente = db.query(Nota).filter(
                Nota.estudiante_id == estudiante.id,
                Nota.curso_id == curso.id
            ).first()
            
            if nota_existente:
                print(f'Ya existe nota para {curso.nombre}')
                continue
            
            # Crear nueva nota
            nueva_nota = Nota(
                estudiante_id=estudiante.id,
                curso_id=curso.id,
                tipo_evaluacion='Evaluación Regular',
                nota1=Decimal('15.5'),
                nota2=Decimal('16.0'),
                nota3=Decimal('14.5'),
                nota4=Decimal('17.0'),
                nota_final=Decimal('15.75'),
                estado='APROBADO',
                peso=Decimal('1.0'),
                fecha_evaluacion=date.today(),
                observaciones='Notas de prueba'
            )
            
            db.add(nueva_nota)
            print(f'Nota creada para {curso.nombre}')
            notas_creadas += 1
        
        db.commit()
        print(f'Se crearon {notas_creadas} notas exitosamente')
        return True
        
    except Exception as e:
        print(f'Error: {e}')
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    crear_notas_prueba()