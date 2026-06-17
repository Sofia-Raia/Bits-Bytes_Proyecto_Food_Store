# app/modules/auth/dependencies.py
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlmodel import Session

from app.core.database import get_session
from app.modules.auth.models import Usuario
from app.modules.auth.repository import AuthRepository
from app.modules.auth.security import decode_token


class CookieBearerScheme(OAuth2PasswordBearer):
    """
    Extrae el access token exclusivamente desde la cookie HttpOnly 'access_token'.

    Hereda de OAuth2PasswordBearer para preservar la integración con OpenAPI/Swagger
    (tokenUrl, esquema Bearer en la documentación).

    El header Authorization fue descartado a propósito: si lo permitiéramos,
    el frontend tendría que manipular el token en texto plano, anulando el
    beneficio de la cookie HttpOnly (inmune a XSS por no ser accesible desde JS).
    """

    async def __call__(self, request: Request) -> str | None:
        token = request.cookies.get("access_token")
        if not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No autenticado",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        return token


# tokenUrl apunta al endpoint de login (usado por OpenAPI para documentación)
_cookie_scheme = CookieBearerScheme(tokenUrl="/auth/login")

# Variante sin auto_error: para endpoints públicos que ajustan su comportamiento
# según el rol del usuario logueado (ej: el catálogo muestra inactivos solo a
# ADMIN/STOCK), pero siguen respondiendo a usuarios anónimos.
_cookie_scheme_optional = CookieBearerScheme(tokenUrl="/auth/login", auto_error=False)


def get_current_user_optional(
    token: str | None = Depends(_cookie_scheme_optional),
    session: Session = Depends(get_session),
) -> tuple[Usuario, list[str]] | None:
    """
    Igual que get_current_user pero NUNCA lanza 401: devuelve (usuario, roles) si
    hay una sesión válida, o None si no hay token o el token es inválido/expirado.
    Pensado para endpoints públicos cuya respuesta varía según el rol.
    """
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        email: str = payload.get("sub", "")
        if not email:
            return None
    except (JWTError, ValueError):
        return None

    repo = AuthRepository(session)
    user = repo.get_active_by_email(email)
    if not user:
        return None

    roles = repo.get_roles(user.id)
    return user, roles


def get_current_user(
    token: str = Depends(_cookie_scheme),
    session: Session = Depends(get_session),
) -> tuple[Usuario, list[str]]:
    """
    Valida el access token desde la cookie y devuelve (usuario, roles).
    Lanza 401 si el token es inválido, expirado o no es de tipo 'access'.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("tipo de token incorrecto")
        email: str = payload.get("sub", "")
        if not email:
            raise ValueError("sub vacío")
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = AuthRepository(session)
    user = repo.get_active_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    roles = repo.get_roles(user.id)
    return user, roles


def require_role(roles_permitidos: list[str]) -> Callable:
    """
    Dependencia parametrizada de FastAPI para control de acceso por rol.

    Uso en un router:
        @router.post("/", dependencies=[Depends(require_role(["ADMIN", "STOCK"]))])

    O como dependencia con retorno:
        current = Depends(require_role(["ADMIN", "STOCK"]))

    Lanza 403 si el usuario autenticado no posee ninguno de los roles indicados.
    Lanza 401 (vía get_current_user) si no hay sesión activa.
    """
    def _checker(
        current: tuple[Usuario, list[str]] = Depends(get_current_user),
    ) -> tuple[Usuario, list[str]]:
        user, roles = current
        if not any(r in roles_permitidos for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requiere uno de los roles: {roles_permitidos}",
            )
        return user, roles

    return _checker


# Atajo para el caso más común. Todos los Depends(require_admin) existentes
# siguen funcionando sin cambios: _checker tiene la misma firma que la función
# require_admin anterior.
require_admin = require_role(["ADMIN"])
