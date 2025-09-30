from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base

# Importar todos los routers de los módulos
from app.modules.auth.routes import router as auth_router
from app.modules.student.routes import router as student_router
from app.modules.teacher.routes import router as teacher_router
from app.modules.admin.routes import router as admin_router

# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Crear la aplicación FastAPI
app = FastAPI(
    title="Sistema de Notas Académico",
    description="API modular para gestión de notas académicas con roles diferenciados",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir todos los routers con prefijos organizados
app.include_router(auth_router, prefix="/api/v1", tags=["Autenticación"])
app.include_router(student_router, prefix="/api/v1", tags=["Estudiante"])
app.include_router(teacher_router, prefix="/api/v1", tags=["Docente"])
app.include_router(admin_router, prefix="/api/v1", tags=["Administrador"])

@app.get("/")
def read_root():
    return {
        "mensaje": "Sistema de Notas Académico API 🎓",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "API funcionando correctamente"}