# app/core/middleware/logging_middleware.py
"""
Middleware de logging para Food Store API.

Responsabilidades:
- Genera un request_id (UUID4) por request y lo guarda en request.state.request_id.
- Agrega el header X-Request-ID a la respuesta.
- Loguea entrada (método, path, IP) y salida (status, duración en ms).

Paths excluidos (para no llenar los logs de health-checks y tráfico de documentación):
    /health, /docs, /openapi.json, /redoc
"""
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.logger import get_logger

logger = get_logger(__name__)

# Paths que no se loguean ni reciben request_id (reducen ruido en development)
EXCLUDED_PATHS: frozenset[str] = frozenset({
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
})


def _get_client_ip(request: Request) -> str:
    """
    Extrae la IP del cliente respetando X-Forwarded-For (para proxies/load balancers).
    Usa la primera IP de la cadena (la del cliente original).
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "desconocida"


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware que loguea cada request/response e inyecta request_id.

    El request_id queda en request.state.request_id y en el header X-Request-ID
    de la respuesta. Los exception handlers lo usan para incluirlo en el JSON de error.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Paths excluidos: pasar sin loguear ni asignar request_id
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        # Generar y persistir request_id
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        client_ip = _get_client_ip(request)
        logger.info(
            "→ %s %s | ip=%s | request_id=%s",
            request.method,
            request.url.path,
            client_ip,
            request_id,
        )

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1_000

        logger.info(
            "← %s %s | status=%s | %.1f ms | request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )

        response.headers["X-Request-ID"] = request_id
        return response
