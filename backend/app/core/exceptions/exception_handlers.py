# app/core/exceptions/exception_handlers.py
"""
Handlers de excepciones para Food Store API.

Todos los errores devuelven el mismo formato JSON unificado:
    {
        "error": {
            "code":       "RESOURCE_NOT_FOUND",   # string estable
            "message":    "Producto no encontrado",
            "request_id": "4f3a...",               # de request.state (logging middleware)
            "timestamp":  "2026-05-27T18:00:00Z"
        }
    }

Registro:
    from app.core.exceptions.exception_handlers import register_exception_handlers
    register_exception_handlers(app)
"""
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions.custom_exceptions import AppError
from app.core.logger import get_logger

logger = get_logger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "timestamp": _now_iso(),
            }
        },
    )


def _code_from_status(status_code: int) -> str:
    """Deriva un code string estable a partir del status HTTP."""
    _map = {
        400: "BAD_REQUEST",
        401: "AUTHENTICATION_ERROR",
        403: "AUTHORIZATION_ERROR",
        404: "RESOURCE_NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    return _map.get(status_code, f"HTTP_{status_code}")


# ── Handlers ──────────────────────────────────────────────────────────────────

async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """Captura cualquier excepción de dominio (AppError y subclases)."""
    request_id = _get_request_id(request)
    logger.warning(
        "AppError [%s] %s | request_id=%s | path=%s",
        exc.code,
        exc.message,
        request_id,
        request.url.path,
    )
    return _error_response(exc.status_code, exc.code, exc.message, request_id)


async def _handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Captura HTTPException de FastAPI/Starlette (incluyendo las de routers y dependencies)."""
    request_id = _get_request_id(request)
    code = _code_from_status(exc.status_code)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    logger.warning(
        "HTTPException %s [%s] %s | request_id=%s | path=%s",
        exc.status_code,
        code,
        detail,
        request_id,
        request.url.path,
    )
    return _error_response(exc.status_code, code, detail, request_id)


async def _handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Captura errores de validación de Pydantic / FastAPI (body, query params, etc.)."""
    request_id = _get_request_id(request)
    # Construye lista de errores por campo
    fields = [
        {
            "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
            "message": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    logger.warning(
        "ValidationError %s campo(s) | request_id=%s | path=%s",
        len(fields),
        request_id,
        request.url.path,
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Error de validación en los datos de entrada",
                "fields": fields,
                "request_id": request_id,
                "timestamp": _now_iso(),
            }
        },
    )


async def _handle_sqlalchemy_error(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """
    Captura errores de SQLAlchemy.
    - IntegrityError (FK, unique, not-null violados) → 409 CONFLICT
    - Resto → 500 genérico (no se filtran detalles internos al cliente)
    """
    request_id = _get_request_id(request)
    if isinstance(exc, IntegrityError):
        logger.warning(
            "IntegrityError | request_id=%s | path=%s | %s",
            request_id,
            request.url.path,
            str(exc.orig),
        )
        return _error_response(409, "CONFLICT", "Conflicto de integridad en la base de datos", request_id)

    logger.error(
        "SQLAlchemyError inesperado | request_id=%s | path=%s | %s",
        request_id,
        request.url.path,
        str(exc),
        exc_info=True,
    )
    return _error_response(500, "INTERNAL_SERVER_ERROR", "Error interno del servidor", request_id)


async def _handle_generic_exception(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all: cualquier excepción no capturada → 500 genérico."""
    request_id = _get_request_id(request)
    logger.error(
        "Excepción inesperada | request_id=%s | path=%s | %s",
        request_id,
        request.url.path,
        str(exc),
        exc_info=True,
    )
    return _error_response(500, "INTERNAL_SERVER_ERROR", "Error interno del servidor", request_id)


# ── Registro ──────────────────────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """
    Registra todos los handlers en la aplicación FastAPI.
    Llamar desde main.py después de crear la app.
    """
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(SQLAlchemyError, _handle_sqlalchemy_error)
    app.add_exception_handler(Exception, _handle_generic_exception)
