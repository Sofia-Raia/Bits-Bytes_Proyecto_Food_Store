# app/modules/auth/models.py
# Los modelos de dominio viven en usuarios/models.py.
# Este módulo los re-exporta para mantener compatibilidad con imports existentes.
from app.modules.usuarios.models import Rol, Usuario, UsuarioRol, RefreshToken  # noqa: F401

__all__ = ["Rol", "Usuario", "UsuarioRol", "RefreshToken"]
