# tests/integration/test_categorias.py
"""
Tests de integración — módulo categorias.

Cubre: crear raíz/subcategoría, listar, árbol, update, desactivar/reactivar,
ciclo en árbol (400 BUSINESS_RULE), padre propio (400 BUSINESS_RULE) y 403.
"""
import pytest


pytestmark = pytest.mark.integration


# ── Helpers ───────────────────────────────────────────────────────────────────

def _crear_categoria(client, headers: dict, nombre: str, parent_id: int | None = None) -> dict:
    payload: dict = {"nombre": nombre}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    resp = client.post("/api/v1/categorias/", json=payload, headers=headers)
    assert resp.status_code == 201, f"Fallo crear categoría: {resp.text}"
    return resp.json()


# ── 1. Crear categoría raíz ───────────────────────────────────────────────────

def test_crear_categoria_raiz(client, admin_auth_headers):
    """ADMIN crea una categoría sin padre → 201 con código CAT-NNNN."""
    resp = client.post(
        "/api/v1/categorias/",
        json={"nombre": "Bebidas"},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Bebidas"
    assert data["parent_id"] is None
    assert data["activo"] is True
    assert data["codigo"].startswith("CAT-")


# ── 2. Crear subcategoría ─────────────────────────────────────────────────────

def test_crear_subcategoria(client, admin_auth_headers):
    """Crear una categoría hija (con parent_id válido) → 201."""
    padre = _crear_categoria(client, admin_auth_headers, "Comidas")
    padre_id = padre["id"]

    resp = client.post(
        "/api/v1/categorias/",
        json={"nombre": "Entradas", "parent_id": padre_id},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["parent_id"] == padre_id
    assert data["nombre"] == "Entradas"


# ── 3. Listar categorías (público) ───────────────────────────────────────────

def test_listar_categorias_publico(client, admin_auth_headers):
    """GET /categorias/ es público y devuelve data/total."""
    _crear_categoria(client, admin_auth_headers, "Cat Lista A")
    _crear_categoria(client, admin_auth_headers, "Cat Lista B")

    resp = client.get("/api/v1/categorias/")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 2


# ── 4. Árbol de categorías ────────────────────────────────────────────────────

def test_get_tree_categorias(client, admin_auth_headers):
    """GET /categorias/tree devuelve el árbol jerárquico (requiere auth)."""
    padre = _crear_categoria(client, admin_auth_headers, "Árbol Padre")
    _crear_categoria(client, admin_auth_headers, "Árbol Hijo", parent_id=padre["id"])

    resp = client.get("/api/v1/categorias/tree", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    # Debe haber al menos el padre en el árbol raíz
    nombres_raiz = [c["nombre"] for c in body["data"]]
    assert "Árbol Padre" in nombres_raiz


# ── 5. Actualizar categoría ───────────────────────────────────────────────────

def test_update_categoria(client, admin_auth_headers):
    """PATCH /categorias/{id} actualiza el nombre → 200."""
    cat = _crear_categoria(client, admin_auth_headers, "Cat Update Old")
    cat_id = cat["id"]

    resp = client.patch(
        f"/api/v1/categorias/{cat_id}",
        json={"nombre": "Cat Update New"},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Cat Update New"


# ── 6. Desactivar categoría ───────────────────────────────────────────────────

def test_desactivar_categoria(client, admin_auth_headers):
    """DELETE /categorias/{id} (soft delete) → 204 y activo=False."""
    cat = _crear_categoria(client, admin_auth_headers, "Cat Desactivar")
    cat_id = cat["id"]

    del_resp = client.delete(f"/api/v1/categorias/{cat_id}", headers=admin_auth_headers)
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/v1/categorias/{cat_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["activo"] is False


# ── 7. Reactivar categoría ────────────────────────────────────────────────────

def test_reactivar_categoria(client, admin_auth_headers):
    """PATCH /categorias/{id}/reactivar vuelve la categoría a activo → 200."""
    cat = _crear_categoria(client, admin_auth_headers, "Cat Reactivar")
    cat_id = cat["id"]

    client.delete(f"/api/v1/categorias/{cat_id}", headers=admin_auth_headers)

    resp = client.patch(
        f"/api/v1/categorias/{cat_id}/reactivar",
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["activo"] is True


# ── 8. Detectar ciclo → 400 BUSINESS_RULE ────────────────────────────────────

def test_ciclo_en_arbol_categorias(client, admin_auth_headers):
    """
    Crear un ciclo A → B → A viola la restricción de árbol
    → 400 con code BUSINESS_RULE.
    Flujo: crear A (raíz), crear B como hijo de A, intentar poner A como hijo de B.
    """
    cat_a = _crear_categoria(client, admin_auth_headers, "Cat Ciclo A")
    cat_b = _crear_categoria(
        client, admin_auth_headers, "Cat Ciclo B", parent_id=cat_a["id"]
    )

    # Intentar que A pase a ser hijo de B → crearía el ciclo A→B→A
    resp = client.patch(
        f"/api/v1/categorias/{cat_a['id']}",
        json={"parent_id": cat_b["id"]},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["code"] == "BUSINESS_RULE"


# ── 9. Padre propio → 400 BUSINESS_RULE ──────────────────────────────────────

def test_padre_propio_devuelve_business_rule(client, admin_auth_headers):
    """
    Una categoría no puede ser su propio padre
    → 400 con code BUSINESS_RULE.
    """
    cat = _crear_categoria(client, admin_auth_headers, "Cat Self Parent")
    cat_id = cat["id"]

    resp = client.patch(
        f"/api/v1/categorias/{cat_id}",
        json={"parent_id": cat_id},   # padre = sí mismo
        headers=admin_auth_headers,
    )
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["code"] == "BUSINESS_RULE"


# ── 10. CLIENT no puede crear categorías → 403 ───────────────────────────────

def test_crear_categoria_como_client_devuelve_403(client, client_auth_headers):
    """POST /categorias/ como CLIENT devuelve 403 AUTHORIZATION_ERROR."""
    resp = client.post(
        "/api/v1/categorias/",
        json={"nombre": "Cat Client Ilegal"},
        headers=client_auth_headers,
    )
    assert resp.status_code == 403
    error = resp.json()["error"]
    assert error["code"] == "AUTHORIZATION_ERROR"
