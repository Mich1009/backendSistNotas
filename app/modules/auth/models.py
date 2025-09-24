# Importar modelos existentes del módulo principal
from app.shared import User, PasswordResetToken, RoleEnum

# Re-exportar para mantener compatibilidad
__all__ = ["User", "PasswordResetToken", "RoleEnum"]