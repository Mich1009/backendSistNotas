#!/usr/bin/env python3
"""
Script para actualizar la base de datos con las columnas faltantes
"""
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sqlalchemy import text
from app.database import engine

def update_database():
    """Actualiza la base de datos con las columnas faltantes"""
    try:
        with engine.connect() as conn:
            # Agregar columnas faltantes a la tabla cursos
            print("Agregando columnas faltantes a la tabla cursos...")
            
            # Verificar si las columnas ya existen
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'cursos' 
                AND column_name IN ('codigo', 'creditos', 'horas_semanales')
            """))
            existing_columns = [row[0] for row in result]
            
            if 'codigo' not in existing_columns:
                conn.execute(text("ALTER TABLE cursos ADD COLUMN codigo VARCHAR(20)"))
                print("+ Columna 'codigo' agregada")
            else:
                print("+ Columna 'codigo' ya existe")
                
            if 'creditos' not in existing_columns:
                conn.execute(text("ALTER TABLE cursos ADD COLUMN creditos INTEGER"))
                print("+ Columna 'creditos' agregada")
            else:
                print("+ Columna 'creditos' ya existe")
                
            if 'horas_semanales' not in existing_columns:
                conn.execute(text("ALTER TABLE cursos ADD COLUMN horas_semanales INTEGER"))
                print("+ Columna 'horas_semanales' agregada")
            else:
                print("+ Columna 'horas_semanales' ya existe")
            
            # Agregar columnas faltantes a la tabla matriculas
            print("\nAgregando columnas faltantes a la tabla matriculas...")
            
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'matriculas' 
                AND column_name = 'curso_id'
            """))
            existing_columns = [row[0] for row in result]
            
            if 'curso_id' not in existing_columns:
                conn.execute(text("ALTER TABLE matriculas ADD COLUMN curso_id INTEGER REFERENCES cursos(id)"))
                print("+ Columna 'curso_id' agregada a matriculas")
            else:
                print("+ Columna 'curso_id' ya existe en matriculas")
            
            # Agregar columnas faltantes a la tabla historial_notas
            print("\nAgregando columnas faltantes a la tabla historial_notas...")
            
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'historial_notas' 
                AND column_name IN ('estudiante_id', 'curso_id', 'modificado_por', 'created_at')
            """))
            existing_columns = [row[0] for row in result]
            
            if 'estudiante_id' not in existing_columns:
                conn.execute(text("ALTER TABLE historial_notas ADD COLUMN estudiante_id INTEGER REFERENCES users(id)"))
                print("+ Columna 'estudiante_id' agregada a historial_notas")
            else:
                print("+ Columna 'estudiante_id' ya existe en historial_notas")
                
            if 'curso_id' not in existing_columns:
                conn.execute(text("ALTER TABLE historial_notas ADD COLUMN curso_id INTEGER REFERENCES cursos(id)"))
                print("+ Columna 'curso_id' agregada a historial_notas")
            else:
                print("+ Columna 'curso_id' ya existe en historial_notas")
                
            if 'modificado_por' not in existing_columns:
                conn.execute(text("ALTER TABLE historial_notas ADD COLUMN modificado_por INTEGER REFERENCES users(id)"))
                print("+ Columna 'modificado_por' agregada a historial_notas")
            else:
                print("+ Columna 'modificado_por' ya existe en historial_notas")
                
            if 'created_at' not in existing_columns:
                conn.execute(text("ALTER TABLE historial_notas ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                print("+ Columna 'created_at' agregada a historial_notas")
            else:
                print("+ Columna 'created_at' ya existe en historial_notas")
            
            # Eliminar columnas obsoletas si existen
            print("\nEliminando columnas obsoletas...")
            
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'historial_notas' 
                AND column_name IN ('motivo_cambio', 'usuario_modificacion', 'fecha_modificacion')
            """))
            obsolete_columns = [row[0] for row in result]
            
            for col in obsolete_columns:
                conn.execute(text(f"ALTER TABLE historial_notas DROP COLUMN {col}"))
                print(f"+ Columna obsoleta '{col}' eliminada")
            
            conn.commit()
            print("\n+ Base de datos actualizada correctamente!")
            
    except Exception as e:
        print(f"Error al actualizar la base de datos: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Actualizando esquema de la base de datos...")
    if update_database():
        print("¡Actualizacion completada exitosamente!")
    else:
        print("Error en la actualizacion")
