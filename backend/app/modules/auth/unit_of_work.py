# app/modules/auth/unit_of_work.py
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.auth.repository import AuthRepository
from app.modules.usuarios.repository import UsuarioRepository


class AuthUnitOfWork(UnitOfWork):
    """
    UoW del módulo auth.
    - auth:     lectura (login, lookup de roles).
    - usuarios: mutaciones de Usuario y UsuarioRol (necesario para register).
                Reutiliza el repo del módulo usuarios para no duplicar lógica.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.auth     = AuthRepository(session)
        self.usuarios = UsuarioRepository(session)
