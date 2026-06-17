# app/core/middleware/timing_middleware.py
"""
Middleware de temporización para Food Store API.

Agrega el header estándar Server-Timing a cada respuesta con la duración total
del request en milisegundos. Loguea un WARNING si la respuesta supera 500 ms.

Referencia: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Server-Timing
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.logger import get_logger

logger = get_logger(__name__)

# Umbral en ms a partir del cual se loguea un WARNING
_SLOW_REQUEST_THRESHOLD_MS: float = 500.0


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Mide la duración total del request (incluyendo el resto del stack de middlewares)
    y agrega el header `Server-Timing: total;dur=<ms>` a la respuesta.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1_000

        # Header estándar Server-Timing
        response.headers["Server-Timing"] = f"total;dur={duration_ms:.1f}"

        if duration_ms > _SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                "Request lento: %s %s tomó %.1f ms (umbral=%s ms)",
                request.method,
                request.url.path,
                duration_ms,
                _SLOW_REQUEST_THRESHOLD_MS,
            )

        return response
