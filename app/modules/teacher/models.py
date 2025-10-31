# Importar modelos existentes del módulo principal
from app.shared import (
    User, RoleEnum, Carrera, Ciclo, Curso, 
    Matricula, Nota, HistorialNota, DescripcionEvaluacion
)

# Re-exportar para mantener compatibilidad
__all__ = [
    "User", "RoleEnum", "Carrera", "Ciclo", 
    "Curso", "Matricula", "Nota", "HistorialNota", "DescripcionEvaluacion"
]