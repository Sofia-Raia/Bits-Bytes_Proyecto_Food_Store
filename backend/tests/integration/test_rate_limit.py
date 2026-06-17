# tests/integration/test_rate_limit.py
"""
Tests de integración — RateLimitMiddleware.

Verifica que el rate limiting funcione correctamente en los auth endpoints
(más estrictos: burst=5, 10/min) y que la respuesta 429 tenga el formato
unificado con los headers correctos.

NOTA: clean_db llama a RateLimitMiddleware.reset_all_limiters() implícitamente
a través del fixture client (que sí lo llama). Los tests de rate limit crean
su propio client sin reset para poder agotar el burst.
"""
import pytest

from app.core.rate_limit.rate_limit_middleware import RateLimitMiddleware


pytestmark = pytest.mark.integration


# ── Helper ────────────────────────────────────────────────────────────────────

def _login_request(client) -> int:
    """Realiza un intento de login y devuelve el status code."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "noexiste@test.com", "password": "cualquier"},
    )
    return resp.status_code


# ── 1. Rate limit excedido en /auth/login → 429 ───────────────────────────────

def test_rate_limit_auth_excedido_devuelve_429(client):
    """
    El auth limiter tiene burst=5 (RATE_LIMIT_AUTH_BURST=5).
    Después de 5 intentos el siguiente devuelve 429.
    
    Se resetean los limiters antes (client fixture lo hace),
    luego se agotan los 5 tokens del burst y se verifica el 429.
    """
    # Agotar el burst (5 tokens) con intentos de login fallidos
    for _ in range(5):
        status = _login_request(client)
        # Los primeros 5 pueden ser 401 (credenciales incorrectas) o 200
        assert status in (200, 401), f"Status inesperado: {status}"

    # El sexto debe ser 429
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "noexiste@test.com", "password": "cualquier"},
    )
    assert resp.status_code == 429
    error = resp.json()["error"]
    assert error["code"] == "RATE_LIMITED"


# ── 2. Respuesta 429 incluye Retry-After y headers X-RateLimit-* ──────────────

def test_rate_limit_429_tiene_headers_correctos(client):
    """
    La respuesta 429 incluye:
    - Retry-After: segundos enteros hasta que se puede reintentar
    - X-RateLimit-Limit: el límite de la ruta
    - X-RateLimit-Remaining: 0 (sin tokens disponibles)
    """
    # Agotar el burst del auth limiter
    for _ in range(5):
        client.post(
            "/api/v1/auth/login",
            json={"email": "x@x.com", "password": "x"},
        )

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "x@x.com", "password": "x"},
    )
    assert resp.status_code == 429

    # Headers obligatorios
    assert "retry-after" in resp.headers
    assert int(resp.headers["retry-after"]) > 0

    assert "x-ratelimit-limit" in resp.headers
    assert int(resp.headers["x-ratelimit-limit"]) > 0

    assert "x-ratelimit-remaining" in resp.headers
    assert resp.headers["x-ratelimit-remaining"] == "0"


# ── 3. Formato unificado en 429 ────────────────────────────────────────────────

def test_rate_limit_respuesta_tiene_formato_unificado(client):
    """La respuesta 429 usa el formato de error unificado del proyecto."""
    for _ in range(5):
        client.post(
            "/api/v1/auth/login",
            json={"email": "y@y.com", "password": "y"},
        )

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "y@y.com", "password": "y"},
    )
    assert resp.status_code == 429
    body = resp.json()
    assert "error" in body
    error = body["error"]
    assert error["code"] == "RATE_LIMITED"
    assert "message" in error
    assert "request_id" in error
    assert "timestamp" in error


# ── 4. Reset de limiters permite volver a hacer requests ─────────────────────

def test_reset_all_limiters_limpia_contadores(client):
    """
    Después de reset_all_limiters(), las IPs vuelven a tener tokens disponibles.
    """
    # Agotar el burst
    for _ in range(5):
        client.post(
            "/api/v1/auth/login",
            json={"email": "z@z.com", "password": "z"},
        )
    resp_429 = client.post(
        "/api/v1/auth/login",
        json={"email": "z@z.com", "password": "z"},
    )
    assert resp_429.status_code == 429

    # Reset
    RateLimitMiddleware.reset_all_limiters()

    # Ahora el primer request pasa (401 por credenciales incorrectas, no 429)
    resp_after = client.post(
        "/api/v1/auth/login",
        json={"email": "z@z.com", "password": "z"},
    )
    assert resp_after.status_code == 401  # No 429
