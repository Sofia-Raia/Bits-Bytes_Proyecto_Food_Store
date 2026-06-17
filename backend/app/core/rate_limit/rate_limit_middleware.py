# app/core/rate_limit/rate_limit_middleware.py
"""
Middleware de rate limiting para Food Store API.

Estrategia:
- default_limiter: aplica a todos los paths no excluidos.
- auth_limiter:    aplica solo a AUTH_PATHS (más estricto).
  Si el path es de auth, se usa auth_limiter Y default_limiter no se aplica.

Clave de cliente: IP extraída de X-Forwarded-For o request.client.host.

Respuesta 429: JSON unificado + headers X-RateLimit-* y Retry-After.

Uso:
    app.add_middleware(RateLimitMiddleware, settings=settings)

    # En tests, limpiar contadores entre pruebas:
    RateLimitMiddleware.reset_all_limiters()
"""
import math

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.logger import get_logger
from app.core.rate_limit.rate_limiter import RateLimiter
from app.core.config import settings

logger = get_logger(__name__)

# Paths de autenticación con límite más estricto
AUTH_PATHS: frozenset[str] = frozenset({
    "/api/v1/auth/login",
    "/api/v1/auth/register",
})

# Paths excluidos del rate limiting (health + documentación)
EXCLUDED_PATHS: frozenset[str] = frozenset({
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
})

# Referencias a los limiters activos (inicializadas al crear el middleware)
_default_limiter: RateLimiter | None = None
_auth_limiter: RateLimiter | None = None


def _get_client_ip(request: Request) -> str:
    """IP del cliente respetando X-Forwarded-For."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _build_429_response(
    path: str,
    retry_after: float,
    request_id: str,
    limit: int,
) -> Response:
    """Construye la respuesta 429 con formato de error unificado y headers estándar."""
    import datetime

    retry_ceil = math.ceil(retry_after)
    body = {
        "error": {
            "code": "RATE_LIMITED",
            "message": "Demasiadas solicitudes. Intentá de nuevo más tarde.",
            "request_id": request_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }
    }
    response = JSONResponse(status_code=429, content=body)
    response.headers["Retry-After"] = str(retry_ceil)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = "0"
    response.headers["X-RateLimit-Reset"] = str(retry_ceil)
    return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware de rate limiting por IP.

    Inicializa los limiters usando los valores de Settings.
    Expone reset_all_limiters() como classmethod para uso en tests.
    """

    def __init__(self, app: ASGIApp, settings) -> None:
        super().__init__(app)
        global _default_limiter, _auth_limiter

        _default_limiter = RateLimiter(
            per_minute=settings.RATE_LIMIT_DEFAULT_PER_MINUTE,
            burst=settings.RATE_LIMIT_DEFAULT_BURST,
        )
        _auth_limiter = RateLimiter(
            per_minute=settings.RATE_LIMIT_AUTH_PER_MINUTE,
            burst=settings.RATE_LIMIT_AUTH_BURST,
            lockout_seconds=settings.RATE_LIMIT_AUTH_LOCKOUT_SECONDS,
        )
        logger.info(
            "RateLimitMiddleware inicializado | default=%s/min burst=%s | auth=%s/min burst=%s",
            settings.RATE_LIMIT_DEFAULT_PER_MINUTE,
            settings.RATE_LIMIT_DEFAULT_BURST,
            settings.RATE_LIMIT_AUTH_PER_MINUTE,
            settings.RATE_LIMIT_AUTH_BURST,
        )

    @classmethod
    def reset_all_limiters(cls) -> None:
        """Limpia todos los buckets de ambos limiters. Llamar entre tests."""
        if _default_limiter is not None:
            _default_limiter.reset()
        if _auth_limiter is not None:
            _auth_limiter.reset()

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Paths excluidos: sin rate limit
        if path in EXCLUDED_PATHS:
            return await call_next(request)

        client_ip = _get_client_ip(request)
        request_id = getattr(request.state, "request_id", "-")

        # Seleccionar limiter según el path
        if path not in AUTH_PATHS:
            return await call_next(request)

        limiter = _auth_limiter
        limit = settings.RATE_LIMIT_AUTH_BURST

        if limiter is None:
            # No debería ocurrir, pero por seguridad dejamos pasar
            return await call_next(request)

        # 1) Si la IP ya está bloqueada por fallos previos, rechazar sin procesar.
        blocked, retry_after = limiter.is_blocked(client_ip)
        if blocked:
            logger.warning(
                "Login bloqueado por intentos fallidos | ip=%s | path=%s | retry_after=%.1fs | request_id=%s",
                client_ip,
                path,
                retry_after,
                request_id,
            )
            return _build_429_response(path, retry_after, request_id, limit)

        # 2) Procesar el intento.
        response = await call_next(request)

        # 3) Sólo los intentos fallidos cuentan: un login/registro exitoso (2xx)
        #    no consume cupo. Cualquier respuesta >= 400 se registra como fallo y,
        #    al agotar el bucket, se activa el lockout configurable.
        if response.status_code >= 400:
            limiter.register_failure(client_ip)

        return response
