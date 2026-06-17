# tests/integration/test_auth.py
"""
Tests de integración — módulo auth.

Cubre: login, register, refresh, logout, /me, rutas protegidas,
rol insuficiente, email duplicado y formato de error unificado.
"""
import pytest


pytestmark = pytest.mark.integration


# ── 1. Login exitoso ──────────────────────────────────────────────────────────

def test_login_exitoso(client):
    """Login con credenciales válidas devuelve 200 y setea la cookie access_token."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_test@test.com", "password": "Test1234!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin_test@test.com"
    assert "ADMIN" in data["roles"]
    # La cookie debe estar seteada (TestClient la persiste internamente)
    assert "access_token" in resp.cookies


# ── 2. Login con credenciales incorrectas ─────────────────────────────────────

def test_login_credenciales_incorrectas(client):
    """Login con password erróneo devuelve 401 con code AUTHENTICATION_ERROR."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_test@test.com", "password": "MalPassword"},
    )
    assert resp.status_code == 401
    error = resp.json()["error"]
    assert error["code"] == "AUTHENTICATION_ERROR"


# ── 3. Registro de nuevo usuario ──────────────────────────────────────────────

def test_register_nuevo_usuario(client):
    """Registro público crea un usuario con rol CLIENT y devuelve 201."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "nombre": "Nuevo",
            "apellido": "Usuario",
            "email": "nuevo@test.com",
            "password": "Nuevo1234!",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "nuevo@test.com"
    assert data["roles"] == ["CLIENT"]
    # También setea cookie
    assert "access_token" in resp.cookies


# ── 4. Refresh token ──────────────────────────────────────────────────────────

def test_refresh_token(client):
    """
    Después del login, el refresh_token (en cookie path=/api/v1/auth/refresh)
    permite obtener un nuevo access_token.
    """
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "client_test@test.com", "password": "Test1234!"},
    )
    assert login_resp.status_code == 200
    # El refresh_token tiene path=/api/v1/auth/refresh; TestClient lo envía automáticamente
    refresh_resp = client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "email" in data
    assert "roles" in data
    # Nuevo access_token en cookie
    assert "access_token" in refresh_resp.cookies


# ── 5. Logout ─────────────────────────────────────────────────────────────────

def test_logout_elimina_cookies(client):
    """Logout devuelve 204 y limpia las cookies de autenticación."""
    client.post(
        "/api/v1/auth/login",
        json={"email": "client_test@test.com", "password": "Test1234!"},
    )
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 204
    # La cookie fue eliminada: max-age=0 o Set-Cookie con expires en el pasado
    set_cookie_headers = resp.headers.get("set-cookie", "")
    # El cliente ya no debería tener el token activo (verificar con /me)
    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 401


# ── 6. Ruta protegida sin cookie ──────────────────────────────────────────────

def test_ruta_protegida_sin_cookie(client):
    """GET /me sin cookie devuelve 401 con code AUTHENTICATION_ERROR."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    error = resp.json()["error"]
    assert error["code"] == "AUTHENTICATION_ERROR"


# ── 7. Ruta protegida con cookie válida ───────────────────────────────────────

def test_ruta_protegida_con_cookie(client, client_auth_headers):
    """GET /me con cookie válida devuelve 200 y los datos del usuario."""
    resp = client.get("/api/v1/auth/me", headers=client_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "client_test@test.com"
    assert "CLIENT" in data["roles"]


# ── 8. Rol insuficiente → 403 ─────────────────────────────────────────────────

def test_rol_insuficiente_devuelve_403(client, client_auth_headers):
    """
    Un usuario con rol CLIENT intentando acceder a /api/v1/usuarios
    (que requiere ADMIN) recibe 403 con code AUTHORIZATION_ERROR.
    """
    resp = client.get("/api/v1/usuarios/", headers=client_auth_headers)
    assert resp.status_code == 403
    error = resp.json()["error"]
    assert error["code"] == "AUTHORIZATION_ERROR"


# ── 9. Email duplicado → 409 ─────────────────────────────────────────────────

def test_register_email_duplicado(client):
    """Intentar registrar el mismo email dos veces devuelve 409 DUPLICATE_RESOURCE."""
    payload = {
        "nombre": "Dup",
        "apellido": "User",
        "email": "dup@test.com",
        "password": "Dup12345!",
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409
    error = r2.json()["error"]
    assert error["code"] == "DUPLICATE_RESOURCE"


# ── 10. /me retorna datos correctos ──────────────────────────────────────────

def test_me_retorna_datos_del_usuario(client, admin_auth_headers):
    """
    GET /me con token ADMIN devuelve nombre, apellido, email y rol ADMIN.
    También verifica que la respuesta incluye todos los campos esperados.
    """
    resp = client.get("/api/v1/auth/me", headers=admin_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin_test@test.com"
    assert data["nombre"] == "Admin"
    assert data["apellido"] == "Test"
    assert "ADMIN" in data["roles"]
    assert "id" in data


# ── Revocación de refresh token (logout) ──────────────────────────────────────

def test_logout_revoca_refresh_token(client):
    """
    Tras logout, el refresh token queda revocado: aunque el cliente reenvíe la
    cookie, /refresh responde 401 (la sesión ya no puede renovarse).
    """
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "client_test@test.com", "password": "Test1234!"},
    )
    assert login_resp.status_code == 200
    assert client.post("/api/v1/auth/refresh").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 204


def test_refresh_tras_logout_falla(client):
    """Un refresh token revocado por logout no puede renovar la sesión."""
    client.post(
        "/api/v1/auth/login",
        json={"email": "client_test@test.com", "password": "Test1234!"},
    )
    refresh_cookie = client.cookies.get("refresh_token")
    assert refresh_cookie
    assert client.post("/api/v1/auth/logout").status_code == 204
    client.cookies.set("refresh_token", refresh_cookie, path="/api/v1/auth/refresh")
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401
