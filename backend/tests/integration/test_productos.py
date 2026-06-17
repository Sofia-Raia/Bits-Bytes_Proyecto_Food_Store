# tests/integration/test_productos.py
"""
Tests de integración — módulo productos.

Cubre: crear como ADMIN/STOCK, listar, get, update, desactivar/reactivar,
MANUFACTURADO sin ingredientes (422), aplicar-margen, 403 como CLIENT y 404.
"""
import pytest


pytestmark = pytest.mark.integration

# ── Payload de producto base para reutilizar ──────────────────────────────────

def _payload_terminado(suffix: str = "") -> dict:
    return {
        "nombre": f"Producto Test{suffix}",
        "tipo": "TERMINADO",
        "precio_base": 1500.00,
        "stock_cantidad": 50,
        "disponible": True,
    }


def _crear_producto(client, headers: dict, payload: dict | None = None) -> dict:
    """Helper: crea un producto y retorna el JSON de la respuesta."""
    if payload is None:
        payload = _payload_terminado()
    resp = client.post("/api/v1/productos/", json=payload, headers=headers)
    assert resp.status_code == 201, f"Fallo al crear producto: {resp.text}"
    return resp.json()


# ── 1. Crear como ADMIN ───────────────────────────────────────────────────────

def test_crear_producto_como_admin(client, admin_auth_headers):
    """ADMIN puede crear un producto TERMINADO → 201 con los datos completos."""
    resp = client.post(
        "/api/v1/productos/",
        json=_payload_terminado(" ADMIN"),
        headers=admin_auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Producto Test ADMIN"
    assert data["tipo"] == "TERMINADO"
    assert data["activo"] is True


# ── 2. Crear como STOCK ───────────────────────────────────────────────────────

def test_crear_producto_como_stock(client, stock_auth_headers):
    """STOCK también puede crear productos → 201."""
    resp = client.post(
        "/api/v1/productos/",
        json=_payload_terminado(" STOCK"),
        headers=stock_auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["nombre"] == "Producto Test STOCK"


# ── 3. Listar paginado ────────────────────────────────────────────────────────

def test_listar_productos_paginado(client, admin_auth_headers):
    """GET /productos/ devuelve data y total; respeta offset/limit."""
    _crear_producto(client, admin_auth_headers, _payload_terminado(" A"))
    _crear_producto(client, admin_auth_headers, _payload_terminado(" B"))

    resp = client.get("/api/v1/productos/?page=1&size=1")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 2
    assert len(body["items"]) == 1
    assert body["page"] == 1
    assert body["size"] == 1


# ── 4. Get por ID ─────────────────────────────────────────────────────────────

def test_get_producto_por_id(client, admin_auth_headers):
    """GET /productos/{id} devuelve el producto correcto."""
    prod = _crear_producto(client, admin_auth_headers)
    prod_id = prod["id"]

    resp = client.get(f"/api/v1/productos/{prod_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == prod_id


# ── 5. Update ─────────────────────────────────────────────────────────────────

def test_update_producto(client, admin_auth_headers):
    """PATCH /productos/{id} como ADMIN actualiza el precio → 200."""
    prod = _crear_producto(client, admin_auth_headers)
    prod_id = prod["id"]

    resp = client.patch(
        f"/api/v1/productos/{prod_id}",
        json={"precio_base": 2000.00},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200
    assert float(resp.json()["precio_base"]) == 2000.00


# ── 6. Desactivar y reactivar ─────────────────────────────────────────────────

def test_desactivar_y_reactivar_producto(client, admin_auth_headers):
    """
    DELETE /productos/{id} desactiva el producto (soft delete → activo=False).
    PATCH /productos/{id}/reactivar lo vuelve activo.
    """
    prod = _crear_producto(client, admin_auth_headers)
    prod_id = prod["id"]

    # Desactivar
    del_resp = client.delete(f"/api/v1/productos/{prod_id}", headers=admin_auth_headers)
    assert del_resp.status_code == 204

    # El GET público no devuelve productos inactivos, usamos admin con incluir_inactivos
    get_resp = client.get(
        f"/api/v1/productos/{prod_id}?incluir_inactivos=true",
        headers=admin_auth_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["activo"] is False

    # Reactivar
    reac_resp = client.patch(
        f"/api/v1/productos/{prod_id}/reactivar",
        headers=admin_auth_headers,
    )
    assert reac_resp.status_code == 200
    assert reac_resp.json()["activo"] is True


# ── 7. MANUFACTURADO sin ingredientes → 422 ───────────────────────────────────

def test_crear_manufacturado_sin_ingredientes(client, admin_auth_headers):
    """
    Crear un producto MANUFACTURADO sin ingredientes viola RN-PI02
    → 422 con code VALIDATION_ERROR.
    """
    resp = client.post(
        "/api/v1/productos/",
        json={
            "nombre": "Manu Sin Ing",
            "tipo": "MANUFACTURADO",
            "precio_base": 500.00,
            "ingredientes": [],   # lista vacía = sin ingredientes
        },
        headers=admin_auth_headers,
    )
    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"


# ── 8. Aplicar margen masivo ──────────────────────────────────────────────────

def test_aplicar_margen_masivo(client, admin_auth_headers, session):
    """
    PATCH /productos/aplicar-margen ajusta el precio de productos MANUFACTURADOS.
    El body requiere scope + producto_ids/categoria_id (RN-PR08/PR09).
    Como el producto del test es TERMINADO, se ignora silenciosamente: el endpoint
    responde 200 con la estructura esperada (actualizados vacío, ignorados con 1).
    """
    prod = _crear_producto(client, admin_auth_headers)
    prod_id = prod["id"]

    resp = client.patch(
        "/api/v1/productos/aplicar-margen",
        json={
            "scope": "productos",
            "producto_ids": [prod_id],
            "margen_porcentaje": 20.0,
        },
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # La respuesta incluye las listas de actualizados e ignorados
    assert "actualizados" in data
    assert "ignorados" in data
    # El TERMINADO se ignora, no se actualiza
    assert len(data["actualizados"]) == 0
    assert len(data["ignorados"]) == 1


# ── 9. CLIENT no puede crear productos → 403 ─────────────────────────────────

def test_crear_producto_como_client_devuelve_403(client, client_auth_headers):
    """POST /productos/ como CLIENT devuelve 403 AUTHORIZATION_ERROR."""
    resp = client.post(
        "/api/v1/productos/",
        json=_payload_terminado(" CLIENT"),
        headers=client_auth_headers,
    )
    assert resp.status_code == 403
    error = resp.json()["error"]
    assert error["code"] == "AUTHORIZATION_ERROR"


# ── 10. Producto inexistente → 404 ────────────────────────────────────────────

def test_get_producto_inexistente_devuelve_404(client):
    """GET /productos/999999 devuelve 404 con code RESOURCE_NOT_FOUND."""
    resp = client.get("/api/v1/productos/999999")
    assert resp.status_code == 404
    error = resp.json()["error"]
    assert error["code"] == "RESOURCE_NOT_FOUND"
