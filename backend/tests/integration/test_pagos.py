# tests/integration/test_pagos.py
"""
Tests de integración — módulo pagos (MercadoPago, Parte 4).

El SDK de MercadoPago se MOCKEA (no se pega a la API real). Cubre:
crear preferencia OK, pedido ajeno (403), pedido no PENDIENTE (409), sin auth (401),
webhook approved (confirma + descuenta stock), webhook idempotente, webhook rejected,
webhook approved con stock insuficiente (200, no 500), confirm refresca estado,
y webhook con payment_id desconocido (200 sin efecto).
"""
import pytest
from sqlmodel import select

from app.core.config import settings


pytestmark = pytest.mark.integration


# ── Mock del SDK de MercadoPago ───────────────────────────────────────────────

class _FakeMPState:
    """Estado configurable por test para el SDK falso."""
    payments: dict[int, dict] = {}
    ultima_preferencia: dict | None = None


def _instalar_fake_sdk(monkeypatch):
    """Reemplaza mercadopago.SDK por un doble de test y habilita MP_ACCESS_TOKEN."""
    _FakeMPState.payments = {}
    _FakeMPState.ultima_preferencia = None

    class _Pref:
        def create(self, data):
            _FakeMPState.ultima_preferencia = data
            # El SDK real de MP devuelve {"status": 201, "response": {...}};
            # el service valida ese status, así que el doble debe incluirlo.
            return {"status": 201, "response": {
                "id": "PREF-TEST-1",
                "init_point": "https://mp.test/checkout/PREF-TEST-1",
                "sandbox_init_point": "https://mp.test/sandbox/PREF-TEST-1",
            }}

    class _Pay:
        def get(self, payment_id):
            return {"response": _FakeMPState.payments.get(int(payment_id), {})}

    class _SDK:
        def __init__(self, token):
            self._token = token

        def preference(self):
            return _Pref()

        def payment(self):
            return _Pay()

    import mercadopago
    monkeypatch.setattr(mercadopago, "SDK", _SDK)
    monkeypatch.setattr(settings, "MP_ACCESS_TOKEN", "TEST-access-token")
    monkeypatch.setattr(settings, "MP_PUBLIC_KEY", "TEST-public-key")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _crear_producto(client, headers, stock=10):
    resp = client.post("/api/v1/productos/", json={
        "nombre": "Producto Pago Test", "tipo": "TERMINADO",
        "precio_base": 1000.00, "stock_cantidad": stock,
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _crear_pedido_mp(client, headers, producto_id, cantidad=1):
    resp = client.post("/api/v1/pedidos/", json={
        "forma_pago_codigo": "MERCADOPAGO",
        "items": [{"producto_id": producto_id, "cantidad": cantidad}],
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _crear_preferencia(client, headers, pedido_id):
    return client.post(
        "/api/v1/pagos/create-preference",
        json={"pedido_id": pedido_id},
        headers=headers,
    )


def _payment_mp(pedido_id, payment_id=12345, status="approved", order_id=999):
    """Construye un dict de pago como el que devuelve sdk.payment().get()."""
    return {
        "id": payment_id,
        "status": status,
        "status_detail": "accredited" if status == "approved" else status,
        "external_reference": str(pedido_id),
        "transaction_amount": 1000.0,
        "payment_method_id": "visa",
        "order": {"id": order_id, "type": "mercadopago"},
    }


# ── 1. Crear preferencia OK ───────────────────────────────────────────────────

def test_crear_preferencia_ok(client, admin_auth_headers, client_auth_headers, monkeypatch):
    """CLIENT dueño de un pedido PENDIENTE crea la preferencia → Pago pendiente + init_point."""
    _instalar_fake_sdk(monkeypatch)
    prod = _crear_producto(client, admin_auth_headers)
    pedido = _crear_pedido_mp(client, client_auth_headers, prod["id"])

    resp = _crear_preferencia(client, client_auth_headers, pedido["id"])
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["preference_id"] == "PREF-TEST-1"
    assert data["init_point"].startswith("https://mp.test/")
    assert data["public_key"] == "TEST-public-key"
    assert data["pago_id"] > 0


# ── 2. Crear sobre pedido ajeno → 403 ─────────────────────────────────────────

def test_crear_preferencia_pedido_ajeno_403(
    client, admin_auth_headers, pedidos_auth_headers, client_auth_headers, monkeypatch
):
    """Un usuario no puede pagar el pedido de otro → 403 AUTHORIZATION_ERROR."""
    _instalar_fake_sdk(monkeypatch)
    prod = _crear_producto(client, admin_auth_headers)
    # El pedido lo crea PEDIDOS para sí mismo (usuario distinto al CLIENT)
    pedido = client.post("/api/v1/pedidos/", json={
        "forma_pago_codigo": "MERCADOPAGO",
        "items": [{"producto_id": prod["id"], "cantidad": 1}],
    }, headers=pedidos_auth_headers).json()

    resp = _crear_preferencia(client, client_auth_headers, pedido["id"])
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTHORIZATION_ERROR"


# ── 3. Crear sobre pedido no PENDIENTE → 409 ──────────────────────────────────

def test_crear_preferencia_pedido_no_pendiente_409(
    client, admin_auth_headers, pedidos_auth_headers, client_auth_headers, monkeypatch
):
    """No se puede pagar un pedido que ya no está PENDIENTE → 409 CONFLICT."""
    _instalar_fake_sdk(monkeypatch)
    prod = _crear_producto(client, admin_auth_headers)
    pedido = _crear_pedido_mp(client, client_auth_headers, prod["id"])

    # PEDIDOS confirma el pedido (pasa a CONFIRMADO)
    adv = client.patch(
        f"/api/v1/pedidos/{pedido['id']}/estado",
        json={"estado_hacia": "CONFIRMADO", "motivo": "Confirmación manual"},
        headers=pedidos_auth_headers,
    )
    assert adv.status_code == 200

    resp = _crear_preferencia(client, client_auth_headers, pedido["id"])
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


# ── 4. Sin auth → 401 ─────────────────────────────────────────────────────────

def test_crear_preferencia_sin_auth_401(client, monkeypatch):
    """Crear preferencia sin cookie → 401 AUTHENTICATION_ERROR."""
    _instalar_fake_sdk(monkeypatch)
    resp = client.post("/api/v1/pagos/create-preference", json={"pedido_id": 1})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTHENTICATION_ERROR"


# ── 5. Webhook approved → Pago aprobado + pedido CONFIRMADO + stock descontado ─

def test_webhook_approved_confirma_y_descuenta_stock(
    client, session, admin_auth_headers, client_auth_headers, monkeypatch
):
    _instalar_fake_sdk(monkeypatch)
    from app.modules.productos.models import Producto
    from app.modules.pagos.models import Pago

    prod = _crear_producto(client, admin_auth_headers, stock=10)
    pedido = _crear_pedido_mp(client, client_auth_headers, prod["id"], cantidad=3)
    _crear_preferencia(client, client_auth_headers, pedido["id"])

    payment_id = 12345
    _FakeMPState.payments[payment_id] = _payment_mp(pedido["id"], payment_id, "approved")

    resp = client.post(
        "/api/v1/pagos/webhook",
        json={"type": "payment", "data": {"id": payment_id}},
    )
    assert resp.status_code == 200

    # Pago aprobado
    session.expire_all()
    pago = session.exec(select(Pago).where(Pago.pedido_id == pedido["id"])).first()
    assert pago.estado == "aprobado"
    assert pago.mp_payment_id == payment_id
    # Campos completos del ERD v7 persistidos desde MP
    assert pago.payment_method_id == "visa"
    assert pago.transaction_amount is not None
    assert pago.external_reference is not None

    # Pedido CONFIRMADO
    ped = client.get(f"/api/v1/pedidos/{pedido['id']}", headers=client_auth_headers).json()
    assert ped["estado_codigo"] == "CONFIRMADO"

    # Stock descontado (10 - 3)
    prod_db = session.exec(select(Producto).where(Producto.id == prod["id"])).first()
    assert prod_db.stock_cantidad == 7


# ── 6. Webhook idempotente ────────────────────────────────────────────────────

def test_webhook_idempotente(
    client, session, admin_auth_headers, client_auth_headers, monkeypatch
):
    """Un segundo webhook approved no re-confirma ni vuelve a descontar stock."""
    _instalar_fake_sdk(monkeypatch)
    from app.modules.productos.models import Producto

    prod = _crear_producto(client, admin_auth_headers, stock=10)
    pedido = _crear_pedido_mp(client, client_auth_headers, prod["id"], cantidad=3)
    _crear_preferencia(client, client_auth_headers, pedido["id"])

    payment_id = 22222
    _FakeMPState.payments[payment_id] = _payment_mp(pedido["id"], payment_id, "approved")
    body = {"type": "payment", "data": {"id": payment_id}}

    assert client.post("/api/v1/pagos/webhook", json=body).status_code == 200
    assert client.post("/api/v1/pagos/webhook", json=body).status_code == 200

    # Stock descontado una sola vez (10 - 3 = 7)
    session.expire_all()
    prod_db = session.exec(select(Producto).where(Producto.id == prod["id"])).first()
    assert prod_db.stock_cantidad == 7


# ── 7. Webhook rejected → Pago rechazado + pedido sigue PENDIENTE ─────────────

def test_webhook_rejected_no_confirma(
    client, session, admin_auth_headers, client_auth_headers, monkeypatch
):
    _instalar_fake_sdk(monkeypatch)
    from app.modules.pagos.models import Pago

    prod = _crear_producto(client, admin_auth_headers, stock=10)
    pedido = _crear_pedido_mp(client, client_auth_headers, prod["id"], cantidad=2)
    _crear_preferencia(client, client_auth_headers, pedido["id"])

    payment_id = 33333
    _FakeMPState.payments[payment_id] = _payment_mp(pedido["id"], payment_id, "rejected")

    resp = client.post(
        "/api/v1/pagos/webhook",
        json={"type": "payment", "data": {"id": payment_id}},
    )
    assert resp.status_code == 200

    session.expire_all()
    pago = session.exec(select(Pago).where(Pago.pedido_id == pedido["id"])).first()
    assert pago.estado == "rechazado"

    ped = client.get(f"/api/v1/pedidos/{pedido['id']}", headers=client_auth_headers).json()
    assert ped["estado_codigo"] == "PENDIENTE"


# ── 8. Webhook approved con stock insuficiente → 200, pedido sigue PENDIENTE ───

def test_webhook_approved_stock_insuficiente_responde_200(
    client, session, admin_auth_headers, stock_auth_headers, client_auth_headers, monkeypatch
):
    """
    Si el stock se agotó entre crear y pagar: el webhook NO crashea (200),
    el Pago queda aprobado y el pedido sigue en PENDIENTE para revisión del staff.
    """
    _instalar_fake_sdk(monkeypatch)
    from app.modules.productos.models import Producto
    from app.modules.pagos.models import Pago

    prod = _crear_producto(client, admin_auth_headers, stock=3)
    pedido = _crear_pedido_mp(client, client_auth_headers, prod["id"], cantidad=3)
    _crear_preferencia(client, client_auth_headers, pedido["id"])

    # Agotar el stock por fuera (STOCK lo baja a 0 vía update) ANTES de pagar
    upd = client.patch(
        f"/api/v1/productos/{prod['id']}",
        json={"stock_cantidad": 0},
        headers=stock_auth_headers,
    )
    assert upd.status_code == 200

    payment_id = 44444
    _FakeMPState.payments[payment_id] = _payment_mp(pedido["id"], payment_id, "approved")

    resp = client.post(
        "/api/v1/pagos/webhook",
        json={"type": "payment", "data": {"id": payment_id}},
    )
    assert resp.status_code == 200  # nunca 500 a MP

    session.expire_all()
    pago = session.exec(select(Pago).where(Pago.pedido_id == pedido["id"])).first()
    assert pago.estado == "aprobado"  # el pago sí se aprobó

    # El pedido queda PENDIENTE (no se pudo confirmar por falta de stock)
    ped = client.get(f"/api/v1/pedidos/{pedido['id']}", headers=client_auth_headers).json()
    assert ped["estado_codigo"] == "PENDIENTE"
    prod_db = session.exec(select(Producto).where(Producto.id == prod["id"])).first()
    assert prod_db.stock_cantidad == 0  # no se descontó nada por debajo de 0


# ── 9. Confirm refresca estado ────────────────────────────────────────────────

def test_confirm_refresca_estado(
    client, session, admin_auth_headers, client_auth_headers, monkeypatch
):
    """POST /confirm consulta MP, refresca el Pago y devuelve el estado."""
    _instalar_fake_sdk(monkeypatch)

    prod = _crear_producto(client, admin_auth_headers, stock=10)
    pedido = _crear_pedido_mp(client, client_auth_headers, prod["id"], cantidad=1)
    _crear_preferencia(client, client_auth_headers, pedido["id"])

    payment_id = 55555
    _FakeMPState.payments[payment_id] = _payment_mp(pedido["id"], payment_id, "approved")

    resp = client.post(
        "/api/v1/pagos/confirm",
        json={"pedido_id": pedido["id"], "payment_id": payment_id},
        headers=client_auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pedido_id"] == pedido["id"]
    assert data["estado"] == "aprobado"


# ── 10. Webhook con payment_id desconocido → 200 sin efecto ───────────────────

def test_webhook_payment_desconocido_sin_efecto(
    client, session, admin_auth_headers, client_auth_headers, monkeypatch
):
    """Webhook con un payment_id que MP no reconoce → 200, sin cambios."""
    _instalar_fake_sdk(monkeypatch)
    from app.modules.pagos.models import Pago

    prod = _crear_producto(client, admin_auth_headers, stock=10)
    pedido = _crear_pedido_mp(client, client_auth_headers, prod["id"], cantidad=1)
    _crear_preferencia(client, client_auth_headers, pedido["id"])

    # payment_id 99999 NO está en _FakeMPState.payments → MP devuelve {}
    resp = client.post(
        "/api/v1/pagos/webhook",
        json={"type": "payment", "data": {"id": 99999}},
    )
    assert resp.status_code == 200

    # El Pago sigue pendiente
    session.expire_all()
    pago = session.exec(select(Pago).where(Pago.pedido_id == pedido["id"])).first()
    assert pago.estado == "pendiente"
