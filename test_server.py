#!/usr/bin/env python3
"""
Test script para diagnosticar problemas de arranque del servidor
"""

import sys
import os
from pathlib import Path

# Agregar el directorio actual al path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

print("🔍 Iniciando diagnóstico del servidor...")
print(f"📁 Directorio base: {BASE_DIR}")
print(f"🐍 Python version: {sys.version}")
print(f"📂 Directorio actual: {os.getcwd()}")

try:
    print("\n1️⃣ Probando importación de configuración...")
    from app.config import settings

    print(f"✅ Config cargada: {settings.database_url}")

    print("\n2️⃣ Probando conexión a base de datos...")
    from app.database import engine, Base
    from sqlalchemy import text

    # Probar conexión
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 as test"))
        print(f"✅ Base de datos conectada: {result.fetchone()}")

    print("\n3️⃣ Probando importación de modelos...")
    from app.shared.models import User, RoleEnum, Carrera, Ciclo

    print("✅ Modelos importados correctamente")

    print("\n4️⃣ Probando importación de rutas...")
    from app.modules.auth.routes import router as auth_router
    from app.modules.student.routes import router as student_router
    from app.modules.teacher.routes import router as teacher_router
    from app.modules.admin.routes import router as admin_router

    print("✅ Rutas importadas correctamente")

    print("\n5️⃣ Probando creación de la aplicación FastAPI...")
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="Test App")

    # Configurar CORS básico
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Incluir routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(student_router, prefix="/api/v1")
    app.include_router(teacher_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")

    print("✅ Aplicación FastAPI creada correctamente")

    print("\n6️⃣ Probando una ruta simple...")

    @app.get("/test")
    def test_route():
        return {"status": "ok", "message": "Test funcionando"}

    print("✅ Ruta de prueba añadida")

    print("\n🎉 DIAGNÓSTICO COMPLETADO - TODO BIEN")
    print("🚀 El servidor debería arrancar sin problemas")
    print("\n💡 Para arrancar el servidor ejecuta:")
    print("   uvicorn main:app --host 0.0.0.0 --port 9001 --reload")

except Exception as e:
    print(f"\n❌ ERROR ENCONTRADO:")
    print(f"   Tipo: {type(e).__name__}")
    print(f"   Mensaje: {str(e)}")

    import traceback

    print(f"\n🔍 Traceback completo:")
    traceback.print_exc()

    print(f"\n🛠️ POSIBLES SOLUCIONES:")
    print("1. Verificar que el entorno virtual esté activado")
    print("2. Verificar que PostgreSQL esté corriendo")
    print("3. Verificar las credenciales de la base de datos")
    print("4. Ejecutar: pip install -r requirements.txt")
