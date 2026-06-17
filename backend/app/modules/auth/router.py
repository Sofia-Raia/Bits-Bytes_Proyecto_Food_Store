# app/modules/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.modules.auth import service as auth_service
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import LoginRequest, LoginResponse, RegisterRequest
from app.modules.auth.service import SesionEmitida
from app.modules.usuarios.schemas import UsuarioPublic

router = APIRouter()

# ── Constantes de configuración de cookies ────────────────────────────────────

_IS_PROD         = settings.ENV == "production"
_ACCESS_MAX_AGE  = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60   # segundos
_REFRESH_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS   * 86_400


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """
    Escribe access_token y refresh_token como cookies HttpOnly.

    - httponly=True  → inaccesible desde JavaScript (mitiga XSS)
    - samesite="lax" → bloquea envío en requests cross-site (mitiga CSRF)
    - secure=True    → solo HTTPS (activo en producción)
    """
    _shared = dict(httponly=True, samesite="lax", secure=_IS_PROD)
    response.set_cookie(key="access_token",  value=access_token,  max_age=_ACCESS_MAX_AGE,  path="/", **_shared)
    response.set_cookie(key="refresh_token", value=refresh_token, max_age=_REFRESH_MAX_AGE, path="/", **_shared)


def _clear_auth_cookies(response: Response) -> None:
    """Elimina ambas cookies de autenticación con el mismo path con el que se setearon."""
    _shared = dict(httponly=True, samesite="lax", secure=_IS_PROD)
    response.delete_cookie(key="access_token",  path="/", **_shared)
    response.delete_cookie(key="refresh_token", path="/", **_shared)


def _login_response(response: Response, sesion: SesionEmitida) -> LoginResponse:
    """Setea las cookies de la sesión emitida y arma el body de respuesta."""
    _set_auth_cookies(response, sesion.access_token, sesion.refresh_token)
    return LoginResponse(
        id=sesion.id, email=sesion.email, nombre=sesion.nombre,
        apellido=sesion.apellido, roles=sesion.roles,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
def login(
    data: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> LoginResponse:
    sesion = auth_service.login(session, data.email, data.password)
    return _login_response(response, sesion)


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registro público — crea usuario con rol CLIENT y devuelve sesión activa",
)
def register(
    data: RegisterRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> LoginResponse:
    sesion = auth_service.register(session, data)
    return _login_response(response, sesion)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session: Session = Depends(get_session),
    current=Depends(get_current_user),
) -> None:
    """Revoca los refresh tokens activos del usuario y limpia las cookies."""
    user, _roles = current
    auth_service.revoke_session(session, user.id)
    _clear_auth_cookies(response)


@router.post("/refresh", response_model=LoginResponse)
def refresh(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> LoginResponse:
    """Renueva la sesión usando el refresh token de la cookie (con rotación)."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token ausente")
    sesion = auth_service.rotate_session(session, token)
    return _login_response(response, sesion)


@router.get("/me", response_model=UsuarioPublic)
def get_me(current=Depends(get_current_user)) -> UsuarioPublic:
    user, roles = current
    return UsuarioPublic(
        id=user.id, email=user.email, nombre=user.nombre,
        apellido=user.apellido, celular=user.celular,
        roles=roles, activo=user.activo,
    )