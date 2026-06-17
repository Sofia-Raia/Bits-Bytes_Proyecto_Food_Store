# app/modules/auth/service.py
"""
Service del módulo auth: persistencia y orquestación.

Responsabilidades:
- Autenticar, registrar y revocar sesiones de usuario.
- Orquestar la emisión de tokens (la GENERACIÓN vive en security.py) junto con
  la PERSISTENCIA del refresh token (vive en el repository).
- Toda mutación corre dentro de un AuthUnitOfWork: el commit lo hace el UoW,
  nunca el service ni el router.

No genera JWT ni hashea passwords directamente: delega en app.modules.auth.security.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlmodel import Session

from app.core.config import settings
from app.core.exceptions.custom_exceptions import (
    AuthenticationError, DuplicateResourceError,
)
from app.modules.auth.models import Usuario
from app.modules.auth.repository import AuthRepository
from app.modules.auth.security import (
    create_access_token, create_refresh_token, hash_password, verify_password,
)
from app.modules.auth.unit_of_work import AuthUnitOfWork


class SesionEmitida:
    """
    Datos planos que necesita el router para responder y setear cookies.
    Se construye dentro del bloque UoW (sesión viva) y se devuelve ya
    desacoplado de la sesión, que el UoW cierra al salir del with.
    """

    def __init__(
        self, id: int, email: str, nombre: str, apellido: str,
        roles: List[str], access_token: str, refresh_token: str,
    ) -> None:
        self.id            = id
        self.email         = email
        self.nombre        = nombre
        self.apellido      = apellido
        self.roles         = roles
        self.access_token  = access_token
        self.refresh_token = refresh_token


# ── Helpers de orquestación ───────────────────────────────────────────────────

def _emitir_tokens(uow: AuthUnitOfWork, usuario_id: int, payload: dict) -> tuple[str, str]:
    """
    Genera el par access/refresh y persiste el jti del refresh para poder
    revocarlo en el logout. La generación es pura (security); la persistencia
    es del repo (uow.auth). El service sólo coordina ambas.
    """
    access = create_access_token(payload)
    jti = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    uow.auth.add_refresh_token(usuario_id, jti, expires_at)
    refresh = create_refresh_token(payload, jti)
    return access, refresh


def _sesion_para(uow: AuthUnitOfWork, user: Usuario, roles: List[str]) -> SesionEmitida:
    payload = {"sub": user.email, "roles": roles}
    access, refresh = _emitir_tokens(uow, user.id, payload)
    return SesionEmitida(
        id=user.id, email=user.email, nombre=user.nombre, apellido=user.apellido,
        roles=roles, access_token=access, refresh_token=refresh,
    )


# ── Casos de uso ──────────────────────────────────────────────────────────────

def login(session: Session, email: str, password: str) -> SesionEmitida:
    """Valida credenciales, emite el par de tokens y persiste el refresh (UoW)."""
    with AuthUnitOfWork(session) as uow:
        user = uow.auth.get_active_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError("Credenciales incorrectas")
        roles = uow.auth.get_roles(user.id)
        result = _sesion_para(uow, user, roles)
    return result


def register(session: Session, data: "RegisterRequest") -> SesionEmitida:  # type: ignore[name-defined]
    """
    Registro público (RN-AU07 / T-B04): crea Usuario con rol CLIENT automático
    y deja la sesión iniciada (mismas cookies que /login). Todo atómico en el UoW.
    """
    with AuthUnitOfWork(session) as uow:
        if uow.auth.get_by_email(data.email):
            raise DuplicateResourceError("El email ya está registrado")
        usuario = Usuario(
            nombre=data.nombre,
            apellido=data.apellido,
            email=data.email,
            celular=data.celular,
            password_hash=hash_password(data.password),
        )
        uow.usuarios.add(usuario)
        uow.usuarios.set_roles(usuario.id, ["CLIENT"], admin_id=usuario.id)
        roles = ["CLIENT"]
        result = _sesion_para(uow, usuario, roles)
    return result


def revoke_session(session: Session, usuario_id: int) -> None:
    """Logout: revoca todos los refresh tokens activos del usuario (UoW)."""
    with AuthUnitOfWork(session) as uow:
        uow.auth.revoke_all_for_user(usuario_id)


def rotate_session(session: Session, refresh_jwt: str) -> SesionEmitida:
    """
    Refresh token rotation: valida el refresh vigente, lo revoca y emite uno
    nuevo. Lanza AuthenticationError si el token es inválido/revocado/expirado.
    """
    from jose import JWTError  # import local: jose es detalle de validación de token

    from app.modules.auth.security import decode_token

    try:
        payload = decode_token(refresh_jwt)
        if payload.get("type") != "refresh":
            raise ValueError("tipo incorrecto")
        email: str = payload.get("sub", "")
        jti: str = payload.get("jti", "")
        if not email or not jti:
            raise ValueError("claims incompletos")
    except (JWTError, ValueError):
        raise AuthenticationError("Refresh token inválido o expirado")

    with AuthUnitOfWork(session) as uow:
        registro = uow.auth.get_refresh_token(jti)
        if not registro or registro.revoked_at is not None:
            raise AuthenticationError("Sesión revocada. Iniciá sesión nuevamente.")

        user = uow.auth.get_active_by_email(email)
        if not user:
            raise AuthenticationError("Usuario inactivo o eliminado")

        roles = uow.auth.get_roles(user.id)
        uow.auth.revoke_refresh_token(jti)
        result = _sesion_para(uow, user, roles)
    return result


# ── Lecturas auxiliares (sin mutación) ────────────────────────────────────────

def get_usuario_by_email(session: Session, email: str) -> Optional[Usuario]:
    return AuthRepository(session).get_by_email(email)


def get_usuario_con_roles(session: Session, usuario: Usuario) -> tuple[Usuario, List[str]]:
    roles = AuthRepository(session).get_roles(usuario.id)
    return usuario, roles