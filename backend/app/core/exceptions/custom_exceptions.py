# app/core/exceptions/custom_exceptions.py
"""
Jerarquía de excepciones de dominio para Food Store API.

Cada excepción lleva un status_code HTTP fijo y un code string estable
para que el frontend pueda reaccionar de forma programática sin depender
del mensaje (que puede cambiar).

Uso en un service:
    from app.core.exceptions.custom_exceptions import ResourceNotFoundError
    raise ResourceNotFoundError(f"Producto con id={id} no encontrado.")
"""


class AppError(Exception):
    """
    Clase base para todas las excepciones de dominio.
    El exception handler en exception_handlers.py la captura y la serializa
    como JSON unificado: {"error": {"code", "message", "request_id", "timestamp"}}.
    """

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message

    def __repr__(self) -> str:
        return f"{type(self).__name__}(status={self.status_code}, code={self.code!r}, msg={self.message!r})"


# ── Subclases por status code ─────────────────────────────────────────────────

class ResourceNotFoundError(AppError):
    """HTTP 404 — El recurso solicitado no existe."""

    def __init__(self, message: str = "Recurso no encontrado") -> None:
        super().__init__(
            status_code=404,
            code="RESOURCE_NOT_FOUND",
            message=message,
        )


class ConflictError(AppError):
    """HTTP 409 — Conflicto de estado o de regla de negocio."""

    def __init__(self, message: str = "Conflicto con el estado actual del recurso") -> None:
        super().__init__(
            status_code=409,
            code="CONFLICT",
            message=message,
        )


class DuplicateResourceError(ConflictError):
    """
    HTTP 409 — Intento de crear un recurso que ya existe (email duplicado,
    nombre único violado, etc.).

    Subclase de ConflictError para que `except ConflictError` también la capture,
    pero con code distinto para que el frontend distinga el caso "ya existe".
    """

    def __init__(self, message: str = "El recurso ya existe") -> None:
        # Llama a AppError directamente para usar el code correcto
        AppError.__init__(
            self,
            status_code=409,
            code="DUPLICATE_RESOURCE",
            message=message,
        )


class ValidationError(AppError):
    """HTTP 422 — Error de validación de datos de entrada."""

    def __init__(self, message: str = "Error de validación") -> None:
        super().__init__(
            status_code=422,
            code="VALIDATION_ERROR",
            message=message,
        )


class BusinessRuleError(AppError):
    """HTTP 400 — Violación de regla de negocio (input técnicamente válido, semánticamente incorrecto)."""

    def __init__(self, message: str = "Regla de negocio violada") -> None:
        super().__init__(
            status_code=400,
            code="BUSINESS_RULE",
            message=message,
        )


class AuthenticationError(AppError):
    """HTTP 401 — No autenticado o credenciales inválidas."""

    def __init__(self, message: str = "No autenticado") -> None:
        super().__init__(
            status_code=401,
            code="AUTHENTICATION_ERROR",
            message=message,
        )


class AuthorizationError(AppError):
    """HTTP 403 — Autenticado pero sin permiso para la operación."""

    def __init__(self, message: str = "No autorizado") -> None:
        super().__init__(
            status_code=403,
            code="AUTHORIZATION_ERROR",
            message=message,
        )


class RateLimitExceededError(AppError):
    """HTTP 429 — Demasiadas solicitudes."""

    def __init__(
        self,
        message: str = "Demasiadas solicitudes. Intentá de nuevo más tarde.",
        retry_after: float = 60.0,
    ) -> None:
        super().__init__(
            status_code=429,
            code="RATE_LIMITED",
            message=message,
        )
        self.retry_after = retry_after
