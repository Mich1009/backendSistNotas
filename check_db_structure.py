#!/usr/bin/env python3
"""
Script para verificar la estructura actual de la tabla notas
"""

import psycopg2
from app.config import settings

def check_table_structure():
    try:
        print("Conectando a la base de datos...")
        print(f"URL: {settings.database_url}")
        
        # Conectar directamente con psycopg2
        conn = psycopg2.connect(settings.database_url)
        cur = conn.cursor()
        
        print("Conexión exitosa!")
        
        # Verificar estructura actual de la tabla notas
        cur.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'notas' 
            ORDER BY ordinal_position
        """)
        
        print("\nEstructura actual de la tabla notas:")
        print("-" * 50)
        columns = []
        for row in cur.fetchall():
            nullable = "NULL" if row[2] == "YES" else "NOT NULL"
            print(f"  {row[0]}: {row[1]} ({nullable})")
            columns.append(row[0])
        
        print(f"\nTotal de columnas: {len(columns)}")
        print(f"Columnas encontradas: {columns}")
        
        print("\n" + "=" * 50)
        
        # Verificar si existen datos en la tabla
        cur.execute("SELECT COUNT(*) FROM notas")
        count = cur.fetchone()[0]
        print(f"Total de registros en la tabla notas: {count}")
        
        # Verificar si la tabla tiene la estructura nueva o antigua
        if 'valor_nota' in columns:
            print("\n✅ La tabla tiene la estructura NUEVA")
        else:
            print("\n❌ La tabla tiene la estructura ANTIGUA")
            print("Necesita migración!")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error al verificar la estructura: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_table_structure()