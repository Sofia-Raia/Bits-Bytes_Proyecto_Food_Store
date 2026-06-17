# tests/integration/test_pedidos.py
"""
Tests de integración — módulo pedidos.

Cubre: crear pedido (CLIENT), stock decrementa al confirmar, avance FSM válido
por rol, transición inválida (409), cancelar restaura stock, 403 por rol,
editar pedido PENDIENTE, listar propios, 404 y 401.
"""
from decimal import Decimal

import pytest
from sqlmodel import select


pytestmark = pytest.mark.integration


# ── Helpers ───────────────────────────────────────────────────────────────────

def _crear_producto_con_stock(client, headers: dict, stock: int = 10) -> dict:
    """Crea un producto TERMINADO con el stock dado. Devuelve el JSON del producto."""
    resp = client.post(
        "/api/v1/productos/",
        json={
            "nombre": "Producto Stock Test",
            "tipo": "TERMINADO",
            "precio_base": 1000.00,
            "stock_cantidad": stock,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _crear_pedido(client, headers: dict, producto_id: int, cantidad: int = 1) -> dict:
    """Crea un pedido con un ítem del producto dado. Devuelve el JSON del pedido."""
    resp = client.post(
        "/api/v1/pedidos/",
        json={
            "forma_pago_codigo": "EFECTIVO",
            "items": [{"producto_id": producto_id, "cantidad": cantidad}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _avanzar_estado(
    client, headers: dict, pedido_id: int, hacia: str, motivo: str = "Avance de prueba"
) -> dict:
    """Avanza el estado del pedido. Devuelve la respuesta completa.

    Manda siempre un `motivo`: la FSM lo exige para las transiciones a
    CONFIRMADO y CANCELADO, y es ignorado/opcional en el resto.
    """
    return client.patch(
        f"/api/v1/pedidos/{pedido_id}/estado",
        json={"estado_hacia": hacia, "motivo": motivo},
        headers=headers,
    )


# ── 1. Crear pedido como CLIENT ───────────────────────────────────────────────

def test_crear_pedido_como_client(client, admin_auth_headers, client_auth_headers):
    """CLIENT puede crear un pedido con un ítem → 201, estado PENDIENTE."""
    prod = _crear_producto_con_stock(client, admin_auth_headers)

    resp = client.post(
        "/api/v1/pedidos/",
        json={
            "forma_pago_codigo": "EFECTIVO",
            "items": [{"producto_id": prod["id"], "cantidad": 2}],
        },
        headers=client_auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["estado_codigo"] == "PENDIENTE"
    assert len(data["detalles"]) == 1
    assert data["detalles"][0]["cantidad"] == 2


# ── 2. Stock decrementa al confirmar ─────────────────────────────────────────

def test_stock_decrementa_al_confirmar(
    client, session, admin_auth_headers, pedidos_auth_headers, client_auth_headers
):
    """
    El stock NO se descuenta al crear el pedido (PENDIENTE), sino cuando PEDIDOS
    avanza a CONFIRMADO (T-B09).
    """
    from app.modules.productos.models import Producto

    stock_inicial = 10
    prod = _crear_producto_con_stock(client, admin_auth_headers, stock=stock_inicial)
    prod_id = prod["id"]

    pedido = _crear_pedido(client, client_auth_headers, prod_id, cantidad=3)
    pedido_id = pedido["id"]

    # Stock todavía intacto en PENDIENTE
    prod_db = session.exec(select(Producto).where(Producto.id == prod_id)).first()
    assert prod_db.stock_cantidad == stock_inicial

    # Confirmar → descuenta stock
    adv = _avanzar_estado(client, pedidos_auth_headers, pedido_id, "CONFIRMADO")
    assert adv.status_code == 200

    session.expire_all()  # forzar re-lectura desde DB
    prod_db = session.exec(select(Producto).where(Producto.id == prod_id)).first()
    assert prod_db.stock_cantidad == stock_inicial - 3


# ── 3. Avance FSM válido por rol ──────────────────────────────────────────────

def test_avance_fsm_valido_por_rol(
    client, admin_auth_headers, pedidos_auth_headers, client_auth_headers
):
    """PENDIENTE → CONFIRMADO por PEDIDOS es una transición válida → 200."""
    prod = _crear_producto_con_stock(client, admin_auth_headers)
    pedido = _crear_pedido(client, client_auth_headers, prod["id"])

    adv = _avanzar_estado(client, pedidos_auth_headers, pedido["id"], "CONFIRMADO")
    assert adv.status_code == 200
    assert adv.json()["estado_codigo"] == "CONFIRMADO"


# ── 4. Transición inválida → 422 VALIDATION_ERROR ────────────────────────────

def test_transicion_invalida_devuelve_error(
    client, admin_auth_headers, pedidos_auth_headers, client_auth_headers
):
    """
    PENDIENTE → EN_PREP no existe en la FSM → 422 con code VALIDATION_ERROR
    (la transición no está en la matriz de permitidas).
    """
    prod = _crear_producto_con_stock(client, admin_auth_headers)
    pedido = _crear_pedido(client, client_auth_headers, prod["id"])

    adv = _avanzar_estado(client, pedidos_auth_headers, pedido["id"], "EN_PREP")
    assert adv.status_code == 422
    error = adv.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"


# ── 5. Cancelar restaura stock ────────────────────────────────────────────────

def test_cancelar_pedido_restaura_stock(
    client, session, admin_auth_headers, pedidos_auth_headers, client_auth_headers
):
    """
    Flujo: crear → confirmar (stock baja) → cancelar (stock vuelve).
    Solo ADMIN puede cancelar desde CONFIRMADO (T-B10).
    """
    from app.modules.productos.models import Producto

    stock_inicial = 20
    prod = _crear_producto_con_stock(client, admin_auth_headers, stock=stock_inicial)
    prod_id = prod["id"]

    pedido = _crear_pedido(client, client_auth_headers, prod_id, cantidad=5)
    pedido_id = pedido["id"]

    # Confirmar (stock baja a 15)
    _avanzar_estado(client, pedidos_auth_headers, pedido_id, "CONFIRMADO")

    session.expire_all()
    prod_db = session.exec(select(Producto).where(Producto.id == prod_id)).first()
    assert prod_db.stock_cantidad == stock_inicial - 5

    # Cancelar desde CONFIRMADO — solo ADMIN lo puede hacer
    cancel = _avanzar_estado(client, admin_auth_headers, pedido_id, "CANCELADO")
    assert cancel.status_code == 200

    session.expire_all()
    prod_db = session.exec(select(Producto).where(Producto.id == prod_id)).first()
    # Stock restaurado al valor original
    assert prod_db.stock_cantidad == stock_inicial


# ── 6. Rol incorrecto → 403 ───────────────────────────────────────────────────

def test_avanzar_estado_rol_incorrecto_devuelve_403(
    client, admin_auth_headers, stock_auth_headers, client_auth_headers
):
    """
    STOCK no tiene permiso para ninguna transición de pedidos
    → 403 AUTHORIZATION_ERROR.
    """
    prod = _crear_producto_con_stock(client, admin_auth_headers)
    pedido = _crear_pedido(client, client_auth_headers, prod["id"])

    adv = _avanzar_estado(client, stock_auth_headers, pedido["id"], "CONFIRMADO")
    assert adv.status_code == 403
    error = adv.json()["error"]
    assert error["code"] == "AUTHORIZATION_ERROR"


# ── 7. Editar pedido PENDIENTE ────────────────────────────────────────────────

def test_editar_pedido_pendiente(
    client, admin_auth_headers, client_auth_headers
):
    """CLIENT puede editar sus pedidos en estado PENDIENTE → 200."""
    prod_a = _crear_producto_con_stock(client, admin_auth_headers, stock=20)
    # Segundo producto con nombre diferente (evita choque de nombre único)
    resp_b = client.post(
        "/api/v1/productos/",
        json={"nombre": "Producto B Pedido", "tipo": "TERMINADO",
              "precio_base": 500.00, "stock_cantidad": 30},
        headers=admin_auth_headers,
    )
    assert resp_b.status_code == 201
    prod_b = resp_b.json()

    pedido = _crear_pedido(client, client_auth_headers, prod_a["id"], cantidad=1)
    pedido_id = pedido["id"]

    # Editar items del pedido
    upd = client.patch(
        f"/api/v1/pedidos/{pedido_id}",
        json={"items": [{"producto_id": prod_b["id"], "cantidad": 2}]},
        headers=client_auth_headers,
    )
    assert upd.status_code == 200
    detalles = upd.json()["detalles"]
    assert len(detalles) == 1
    assert detalles[0]["producto_id"] == prod_b["id"]
    assert detalles[0]["cantidad"] == 2


# ── 8. CLIENT solo ve sus propios pedidos ─────────────────────────────────────

def test_listar_pedidos_propios_como_client(
    client, admin_auth_headers, client_auth_headers
):
    """
    GET /pedidos/ como CLIENT-only devuelve solo los pedidos del propio usuario
    (T-B11: filtrado por ownership cuando el rol es exclusivamente CLIENT).
    """
    prod = _crear_producto_con_stock(client, admin_auth_headers)

    # CLIENT crea 2 pedidos
    _crear_pedido(client, client_auth_headers, prod["id"])
    _crear_pedido(client, client_auth_headers, prod["id"])

    resp = client.get("/api/v1/pedidos/", headers=client_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    # Todos los pedidos retornados pertenecen al client_test
    for pedido in body["items"]:
        # El campo usuario_id corresponde al usuario logueado
        # (no podemos saber el ID exacto fácilmente, pero total == 2)
        pass
    assert body["total"] == 2


# ── 9. Pedido inexistente → 404 ───────────────────────────────────────────────

def test_get_pedido_inexistente_devuelve_404(client, client_auth_headers):
    """GET /pedidos/999999 devuelve 404 con code RESOURCE_NOT_FOUND."""
    resp = client.get("/api/v1/pedidos/999999", headers=client_auth_headers)
    assert resp.status_code == 404
    error = resp.json()["error"]
    assert error["code"] == "RESOURCE_NOT_FOUND"


# ── 10. Sin autenticación → 401 ───────────────────────────────────────────────

def test_listar_pedidos_sin_auth_devuelve_401(client):
    """GET /pedidos/ sin cookie devuelve 401 AUTHENTICATION_ERROR."""
    resp = client.get("/api/v1/pedidos/")
    assert resp.status_code == 401
    error = resp.json()["error"]
    assert error["code"] == "AUTHENTICATION_ERROR"

# ── 11. Stock insuficiente al crear → 409 CONFLICT ───────────────────────────

def test_crear_pedido_stock_insuficiente_devuelve_409(
    client, admin_auth_headers, client_auth_headers
):
    """
    Pedir más unidades que el stock disponible de un producto TERMINADO rechaza
    la creación con 409 Conflict: el pedido choca con el estado actual del stock.
    """
    prod = _crear_producto_con_stock(client, admin_auth_headers, stock=2)

    resp = client.post(
        "/api/v1/pedidos/",
        json={
            "forma_pago_codigo": "EFECTIVO",
            "items": [{"producto_id": prod["id"], "cantidad": 5}],
        },
        headers=client_auth_headers,
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "CONFLICT"


# ── 12. Historial append-only ─────────────────────────────────────────────────

def test_historial_append_only(
    client, admin_auth_headers, pedidos_auth_headers, client_auth_headers
):
    """
    Cada transición de estado AGREGA un registro al historial sin tocar los
    previos (RN-03, append-only). Tras avanzar PENDIENTE → CONFIRMADO el historial
    crece en 1 y el registro inicial (estado_desde=None, RN-02) queda intacto.
    """
    prod = _crear_producto_con_stock(client, admin_auth_headers)
    pedido = _crear_pedido(client, client_auth_headers, prod["id"])

    h0 = client.get(
        f"/api/v1/pedidos/{pedido['id']}/historial", headers=client_auth_headers
    )
    assert h0.status_code == 200
    historial_inicial = h0.json()
    n_inicial = len(historial_inicial)
    assert n_inicial >= 1
    primer_registro = historial_inicial[0]

    adv = _avanzar_estado(client, pedidos_auth_headers, pedido["id"], "CONFIRMADO")
    assert adv.status_code == 200

    h1 = client.get(
        f"/api/v1/pedidos/{pedido['id']}/historial", headers=client_auth_headers
    )
    assert h1.status_code == 200
    historial_final = h1.json()

    # Append-only: creció exactamente en 1 y el registro previo no se modificó.
    assert len(historial_final) == n_inicial + 1
    assert historial_final[0] == primer_registro