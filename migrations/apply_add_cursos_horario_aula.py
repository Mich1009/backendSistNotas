import os
import sys
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from sqlalchemy import text
from app.database import engine

def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE IF EXISTS cursos ADD COLUMN IF NOT EXISTS horario VARCHAR(255)"))
        print("[OK] Column 'horario' ensured on 'cursos'")
        conn.execute(text("ALTER TABLE IF EXISTS cursos ADD COLUMN IF NOT EXISTS aula VARCHAR(100)"))
        print("[OK] Column 'aula' ensured on 'cursos'")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)
    print("[DONE] Migration applied successfully.")