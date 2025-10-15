#!/usr/bin/env python3
"""
Script de migración para actualizar la tabla notas a la nueva estructura
"""

import psycopg2
from app.config import settings

def migrate_notas_table():
    try:
        print("Conectando a la base de datos...")
        conn = psycopg2.connect(settings.database_url)
        conn.autocommit = False  # Usar transacciones
        cur = conn.cursor()
        
        print("Conexión exitosa!")
        
        # Verificar estructura actual
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'notas' 
            ORDER BY ordinal_position
        """)
        
        current_columns = [row[0] for row in cur.fetchall()]
        print(f"Columnas actuales: {current_columns}")
        
        # Si ya tiene valor_nota, no necesita migración
        if 'valor_nota' in current_columns:
            print("✅ La tabla ya tiene la estructura nueva. No se necesita migración.")
            cur.close()
            conn.close()
            return
        
        print("\n🔄 Iniciando migración...")
        
        # Paso 1: Crear tabla temporal con la nueva estructura
        print("1. Creando tabla temporal...")
        cur.execute("""
            CREATE TABLE notas_new (
                id SERIAL PRIMARY KEY,
                estudiante_id INTEGER NOT NULL REFERENCES users(id),
                curso_id INTEGER NOT NULL REFERENCES cursos(id),
                tipo_evaluacion VARCHAR(50) NOT NULL CHECK (tipo_evaluacion IN ('SEMANAL', 'PRACTICA', 'PARCIAL')),
                valor_nota DECIMAL(4,2) NOT NULL CHECK (valor_nota >= 0 AND valor_nota <= 20),
                peso DECIMAL(3,2) NOT NULL,
                fecha_evaluacion DATE NOT NULL,
                observaciones TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            )
        """)
        
        # Paso 2: Migrar datos existentes (si los hay)
        print("2. Verificando datos existentes...")
        cur.execute("SELECT COUNT(*) FROM notas")
        count = cur.fetchone()[0]
        
        if count > 0:
            print(f"   Encontrados {count} registros. Migrando datos...")
            
            # Obtener datos existentes
            cur.execute("""
                SELECT estudiante_id, curso_id, tipo_evaluacion, nota1, nota2, nota3, nota4, 
                       peso, fecha_evaluacion, observaciones, created_at, updated_at
                FROM notas
            """)
            
            for row in cur.fetchall():
                estudiante_id, curso_id, tipo_evaluacion, nota1, nota2, nota3, nota4, peso, fecha_evaluacion, observaciones, created_at, updated_at = row
                
                # Migrar cada nota individual
                notas_individuales = [
                    (nota1, 'Nota 1'),
                    (nota2, 'Nota 2'), 
                    (nota3, 'Nota 3'),
                    (nota4, 'Nota 4')
                ]
                
                for nota_valor, descripcion in notas_individuales:
                    if nota_valor is not None and nota_valor > 0:
                        cur.execute("""
                            INSERT INTO notas_new 
                            (estudiante_id, curso_id, tipo_evaluacion, valor_nota, peso, fecha_evaluacion, observaciones, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (estudiante_id, curso_id, tipo_evaluacion, nota_valor, peso, fecha_evaluacion, 
                              f"{observaciones or ''} - {descripcion}".strip(), created_at, updated_at))
        else:
            print("   No hay datos existentes para migrar.")
        
        # Paso 3: Eliminar tabla antigua y renombrar la nueva
        print("3. Reemplazando tabla antigua...")
        cur.execute("DROP TABLE IF EXISTS notas CASCADE")
        cur.execute("ALTER TABLE notas_new RENAME TO notas")
        
        # Paso 4: Crear índices
        print("4. Creando índices...")
        cur.execute("CREATE INDEX idx_notas_estudiante_curso ON notas(estudiante_id, curso_id)")
        cur.execute("CREATE INDEX idx_notas_tipo_evaluacion ON notas(tipo_evaluacion)")
        cur.execute("CREATE INDEX idx_notas_fecha_evaluacion ON notas(fecha_evaluacion)")
        
        # Paso 5: Agregar comentarios
        print("5. Agregando comentarios...")
        cur.execute("COMMENT ON TABLE notas IS 'Tabla de notas con nueva estructura: SEMANAL (peso 0.1), PRACTICA (peso 0.3), PARCIAL (peso 0.3)'")
        cur.execute("COMMENT ON COLUMN notas.tipo_evaluacion IS 'Tipo de evaluación: SEMANAL, PRACTICA, PARCIAL'")
        cur.execute("COMMENT ON COLUMN notas.valor_nota IS 'Valor de la nota individual (0-20)'")
        cur.execute("COMMENT ON COLUMN notas.peso IS 'Peso de la evaluación: 0.1 para semanales, 0.3 para prácticas y parciales'")
        
        # Confirmar transacción
        conn.commit()
        print("\n✅ Migración completada exitosamente!")
        
        # Verificar nueva estructura
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'notas' 
            ORDER BY ordinal_position
        """)
        
        new_columns = [row[0] for row in cur.fetchall()]
        print(f"Nuevas columnas: {new_columns}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_notas_table()
