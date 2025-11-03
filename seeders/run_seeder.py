#!/usr/bin/env python3
"""
Script para ejecutar el seeder con la configuración correcta de codificación
Este script configura las variables de entorno necesarias para PostgreSQL
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """Configura el entorno y ejecuta el seeder"""

    # Configurar variables de entorno para PostgreSQL
    os.environ["PGCLIENTENCODING"] = "UTF8"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["LC_ALL"] = "en_US.UTF-8"

    # Configurar la codificación de Python
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr.encoding != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8")

    print("🔧 Configurando entorno para PostgreSQL...")
    print(f"   PGCLIENTENCODING: {os.environ.get('PGCLIENTENCODING')}")
    print(f"   PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING')}")

    # Ruta del seeder
    seeder_path = Path(__file__).parent / "seeder.py"

    try:
        print("🚀 Ejecutando seeder...")
        # Ejecutar el seeder como un subproceso con la configuración correcta
        result = subprocess.run(
            [sys.executable, str(seeder_path)],
            env=os.environ,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        # Mostrar la salida
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        if result.returncode == 0:
            print("✅ Seeder completado exitosamente")
        else:
            print(f"❌ Error en seeder (código: {result.returncode})")

    except Exception as e:
        print(f"❌ Error ejecutando seeder: {e}")
        return 1

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
