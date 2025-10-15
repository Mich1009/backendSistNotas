#!/usr/bin/env python3
"""
Script simple para probar el sistema de calificaciones
"""

import psycopg2
from app.config import settings

def test_simple():
    """Prueba simple del sistema"""
    print("🧪 Probando sistema de calificaciones...")
    
    try:
        # Conectar a la base de datos
        conn = psycopg2.connect(settings.database_url)
        cur = conn.cursor()
        
        print("✅ Conexión a base de datos exitosa")
        
        # Verificar estructura de la tabla notas
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'notas' 
            ORDER BY ordinal_position
        """)
        
        columns = [row[0] for row in cur.fetchall()]
        print(f"📋 Columnas de la tabla notas: {columns}")
        
        # Verificar si tiene la estructura correcta
        if 'valor_nota' in columns:
            print("✅ La tabla tiene la estructura NUEVA correcta")
        else:
            print("❌ La tabla NO tiene la estructura correcta")
            return
        
        # Contar registros
        cur.execute("SELECT COUNT(*) FROM notas")
        count = cur.fetchone()[0]
        print(f"📊 Total de notas en la base de datos: {count}")
        
        # Verificar tipos de evaluación disponibles
        cur.execute("SELECT DISTINCT tipo_evaluacion FROM notas")
        tipos = [row[0] for row in cur.fetchall()]
        print(f"📝 Tipos de evaluación encontrados: {tipos}")
        
        # Probar inserción de una nota de prueba
        print("\n🔧 Probando inserción de nota...")
        
        # Buscar un estudiante y curso existentes
        cur.execute("SELECT id FROM users WHERE role = 'ESTUDIANTE' LIMIT 1")
        estudiante_result = cur.fetchone()
        
        cur.execute("SELECT id FROM cursos LIMIT 1")
        curso_result = cur.fetchone()
        
        if estudiante_result and curso_result:
            estudiante_id = estudiante_result[0]
            curso_id = curso_result[0]
            
            print(f"   Estudiante ID: {estudiante_id}")
            print(f"   Curso ID: {curso_id}")
            
            # Insertar nota de prueba
            cur.execute("""
                INSERT INTO notas (estudiante_id, curso_id, tipo_evaluacion, valor_nota, peso, fecha_evaluacion, observaciones)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (estudiante_id, curso_id, 'SEMANAL', 16.5, 0.1, '2024-01-15', 'Nota de prueba'))
            
            conn.commit()
            print("   ✅ Nota de prueba insertada exitosamente")
            
            # Verificar que se insertó
            cur.execute("SELECT COUNT(*) FROM notas WHERE observaciones = 'Nota de prueba'")
            count_test = cur.fetchone()[0]
            print(f"   📊 Notas de prueba encontradas: {count_test}")
            
        else:
            print("   ⚠️  No hay estudiantes o cursos en la base de datos")
        
        cur.close()
        conn.close()
        
        print("\n🎉 Prueba completada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple()
