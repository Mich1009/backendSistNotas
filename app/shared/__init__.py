# Shared components for the modular system
"""
Componentes compartidos del sistema
"""
from .models import (
    User, PasswordResetToken, RoleEnum,
    Carrera, Ciclo, Curso, Matricula,
    Nota, HistorialNota, DescripcionEvaluacion
)
from .enums import StatusEnum, GradeStatusEnum
from .email_service import email_service

__all__ = [
    "User", "PasswordResetToken", "RoleEnum",
    "Carrera", "Ciclo", "Curso", "Matricula", 
    "Nota", "HistorialNota", "DescripcionEvaluacion",
    "StatusEnum", "GradeStatusEnum",
    "email_service"
]