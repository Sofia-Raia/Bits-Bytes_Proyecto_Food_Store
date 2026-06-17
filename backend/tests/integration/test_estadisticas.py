# tests/integration/test_estadisticas.py
"""Tests de integración del módulo de estadísticas."""
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from app.modules.usuarios.models import Usuario

pytestmark = pytest.mark.integration

BASE = "/api/v1/estadisticas"


def _admin_id(session: Session) -> int:
    return session.exec(
        select(Usuario).where(Usuario.email == "admin_test@test.com")
    ).one().id


def test_resumen_ok(
    client, admin_auth_headers, producto_factory, pedido_factory, session
):
    """
    Arrange: 1 pedido PENDIENTE + 1 CANCELADO con el mismo producto.
    Act:     GET /estadisticas/resumen.
    Assert:  ventas_hoy refleja solo el PENDIENTE; CANCELADO no suma.
    """
    uid = _admin_id(session)
    prod = producto_factory(precio="500.00")
    pedido_factory(usuario_id=uid, producto_id=prod["id"], estado="PENDIENTE")
    pedido_factory(usuario_id=uid, producto_id=prod["id"], estado="CANCELADO")

    resp = client.get(f"{BASE}/resumen", headers=admin_auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(str(data["ventas_hoy"])) == Decimal("500.00")
    assert data["pedidos_activos"] == 1
    assert isinstance(data["productos_stock_bajo"], list)


def test_ventas_periodo_ok(
    client, admin_auth_headers, producto_factory, pedido_factory, session
):
    """
    Arrange: 1 pedido PENDIENTE + 1 CANCELADO.
    Act:     GET /estadisticas/ventas (rango por defecto = últimos 30 días).
    Assert:  lista no vacía, campos requeridos presentes, total = solo el PENDIENTE.
    """
    uid = _admin_id(session)
    prod = producto_factory(precio="300.00")
    pedido_factory(usuario_id=uid, producto_id=prod["id"], estado="PENDIENTE")
    pedido_factory(usuario_id=uid, producto_id=prod["id"], estado="CANCELADO")

    resp = client.get(f"{BASE}/ventas", headers=admin_auth_headers)

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    item = items[0]
    assert "periodo" in item and "total_ventas" in item and "cantidad_pedidos" in item
    assert Decimal(str(item["total_ventas"])) == Decimal("300.00")
    assert item["cantidad_pedidos"] == 1


def test_productos_top_ok(
    client, admin_auth_headers, producto_factory, pedido_factory, session, engine_test
):
    """
    Arrange: 1 pedido PENDIENTE a $200 + cambio de precio post-venta + 1 pedido CANCELADO.
    Act:     GET /estadisticas/productos-top.
    Assert:  ingresos usa subtotal_snap (no precio actual) ;
             producto del pedido CANCELADO no aparece.
    """
    from app.modules.productos.models import Producto

    uid = _admin_id(session)
    prod = producto_factory(precio="200.00")
    prod_cancelado = producto_factory(precio="999.00")
    pedido_factory(usuario_id=uid, producto_id=prod["id"], cantidad=1, estado="PENDIENTE")
    pedido_factory(usuario_id=uid, producto_id=prod_cancelado["id"], cantidad=1, estado="CANCELADO")

    with Session(engine_test) as s:
        p = s.get(Producto, prod["id"])
        p.precio_base = Decimal("999.00")
        s.commit()

    resp = client.get(f"{BASE}/productos-top", headers=admin_auth_headers)

    assert resp.status_code == 200
    items = resp.json()
    item = next(i for i in items if i["producto_id"] == prod["id"])
    assert Decimal(str(item["ingresos"])) == Decimal("200.00")
    assert not any(i["producto_id"] == prod_cancelado["id"] for i in items)


def test_pedidos_por_estado_ok(
    client, admin_auth_headers, producto_factory, pedido_factory, session
):
    """
    Arrange: 2 pedidos PENDIENTE + 1 CANCELADO.
    Act:     GET /estadisticas/pedidos-por-estado.
    Assert:  los conteos agrupados son exactos.
    """
    uid = _admin_id(session)
    prod = producto_factory()
    pedido_factory(usuario_id=uid, producto_id=prod["id"], estado="PENDIENTE")
    pedido_factory(usuario_id=uid, producto_id=prod["id"], estado="PENDIENTE")
    pedido_factory(usuario_id=uid, producto_id=prod["id"], estado="CANCELADO")

    resp = client.get(f"{BASE}/pedidos-por-estado", headers=admin_auth_headers)

    assert resp.status_code == 200
    por_estado = {i["estado_codigo"]: i["cantidad"] for i in resp.json()}
    assert por_estado["PENDIENTE"] == 2
    assert por_estado["CANCELADO"] == 1


def test_ingresos_solo_approved(
    client, admin_auth_headers, producto_factory, pedido_factory, session, engine_test
):
    """
    Arrange: 2 pedidos MERCADOPAGO — un Pago approved y otro pending.
    Act:     GET /estadisticas/ingresos.
    Assert:  solo el pago approved suma; pending no aparece.
    """
    from app.modules.pagos.models import Pago

    uid = _admin_id(session)
    prod = producto_factory(precio="300.00")
    ped_ok = pedido_factory(
        usuario_id=uid, producto_id=prod["id"],
        forma_pago_codigo="MERCADOPAGO", estado="CONFIRMADO",
    )
    ped_pend = pedido_factory(
        usuario_id=uid, producto_id=prod["id"],
        forma_pago_codigo="MERCADOPAGO", estado="CONFIRMADO",
    )

    with Session(engine_test) as s:
        s.add(Pago(
            pedido_id=ped_ok["id"],
            monto=Decimal("300.00"),
            mp_payment_id=11111,
            mp_status="approved",
            idempotency_key=uuid4().hex,
        ))
        s.add(Pago(
            pedido_id=ped_pend["id"],
            monto=Decimal("300.00"),
            mp_payment_id=22222,
            mp_status="pending",
            idempotency_key=uuid4().hex,
        ))
        s.commit()

    resp = client.get(f"{BASE}/ingresos", headers=admin_auth_headers)

    assert resp.status_code == 200
    por_fp = {i["forma_pago_codigo"]: i for i in resp.json()["items"]}
    mp = por_fp["MERCADOPAGO"]
    assert mp["cantidad"] == 1
    assert Decimal(str(mp["total"])) == Decimal("300.00")
