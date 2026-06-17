# app/modules/estadisticas/repository.py
"""
Queries de solo lectura para el módulo de estadísticas.

excluye pedidos CANCELADO en ingresos/cantidades.
usa subtotal_snap de DetallePedido para ingresos por producto.
solo pagos con mp_status='approved' para ingresos confirmados.
montos como Decimal, nunca float.
período con fechas date, filtro BETWEEN.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Sequence, Tuple

from sqlalchemy import text
from sqlmodel import Session, func, select

from app.modules.pagos.models import Pago
from app.modules.pedidos.models import DetallePedido, Pedido
from app.modules.productos.models import Producto, TipoProducto

_ESTADOS_EXCLUIDOS = ("CANCELADO",)


class EstadisticasRepository:

    def __init__(self, session: Session) -> None:
        self.session = session

    # ── KPIs ──────────────────────────────────────────────────────────────────

    def get_ventas_hoy(self) -> Decimal:
        hoy = datetime.now(timezone.utc).date()
        result = self.session.exec(
            select(func.coalesce(func.sum(Pedido.total), 0))
            .where(
                Pedido.deleted_at == None,  # noqa: E711
                Pedido.estado_codigo.not_in(_ESTADOS_EXCLUIDOS),
                func.date(Pedido.created_at) == hoy,
            )
        ).one()
        return Decimal(str(result))

    def get_ventas_mes(self) -> Decimal:
        ahora = datetime.now(timezone.utc)
        result = self.session.exec(
            select(func.coalesce(func.sum(Pedido.total), 0))
            .where(
                Pedido.deleted_at == None,  # noqa: E711
                Pedido.estado_codigo.not_in(_ESTADOS_EXCLUIDOS),
                func.extract("year",  Pedido.created_at) == ahora.year,
                func.extract("month", Pedido.created_at) == ahora.month,
            )
        ).one()
        return Decimal(str(result))

    def get_ticket_promedio(self) -> Decimal:
        result = self.session.exec(
            select(func.coalesce(func.avg(Pedido.total), 0))
            .where(
                Pedido.deleted_at == None,  # noqa: E711
                Pedido.estado_codigo.not_in(_ESTADOS_EXCLUIDOS),
            )
        ).one()
        return Decimal(str(result))

    def get_pedidos_activos(self) -> int:
        result = self.session.exec(
            select(func.count())
            .where(
                Pedido.deleted_at == None,  # noqa: E711
                Pedido.estado_codigo.not_in((*_ESTADOS_EXCLUIDOS, "ENTREGADO")),
            )
        ).one()
        return int(result)

    # ── Ventas por período  ───────────────────────────────────────────

    def get_ventas_periodo(
        self, desde: date, hasta: date, agrupacion: str
    ) -> List[Tuple[str, Decimal, int]]:
        trunc = agrupacion if agrupacion in ("day", "week", "month") else "day"
        rows = self.session.execute(
            text(
                """
                SELECT
                    DATE_TRUNC(:trunc, created_at)::date::text AS periodo,
                    COALESCE(SUM(total), 0)                    AS total_ventas,
                    COUNT(*)                                   AS cantidad_pedidos
                FROM pedidos
                WHERE deleted_at IS NULL
                  AND estado_codigo != 'CANCELADO'
                  AND created_at::date BETWEEN :desde AND :hasta
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"trunc": trunc, "desde": desde, "hasta": hasta},
        ).fetchall()
        return [(r[0], Decimal(str(r[1])), int(r[2])) for r in rows]

    # ── Top productos ────────────────────────────────────────────────

    def get_productos_top(self, limit: int) -> List[Tuple[int, str, Decimal, int]]:
        rows = self.session.execute(
            text(
                """
                SELECT
                    dp.producto_id,
                    dp.nombre_snapshot                      AS nombre,
                    COALESCE(SUM(dp.subtotal_snap), 0)      AS ingresos,
                    SUM(dp.cantidad)                        AS cantidad_vendida
                FROM detalle_pedidos dp
                JOIN pedidos p ON p.id = dp.pedido_id
                WHERE p.deleted_at IS NULL
                  AND p.estado_codigo != 'CANCELADO'
                GROUP BY dp.producto_id, dp.nombre_snapshot
                ORDER BY ingresos DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).fetchall()
        return [(int(r[0]), r[1], Decimal(str(r[2])), int(r[3])) for r in rows]

    # ── Pedidos por estado ────────────────────────────────────────────────────

    def get_pedidos_por_estado(self) -> List[Tuple[str, int]]:
        rows = self.session.exec(
            select(Pedido.estado_codigo, func.count())
            .where(Pedido.deleted_at == None)  # noqa: E711
            .group_by(Pedido.estado_codigo)
            .order_by(Pedido.estado_codigo)
        ).all()
        return [(r[0], int(r[1])) for r in rows]

    # ── Productos con stock bajo ──────────────────────────────────────────────

    def get_stock_bajo(self, umbral: int = 5) -> List[Tuple[int, str, int]]:
        rows = self.session.exec(
            select(Producto.id, Producto.nombre, Producto.stock_cantidad)
            .where(
                Producto.deleted_at == None,  # noqa: E711
                Producto.tipo == TipoProducto.TERMINADO,
                Producto.stock_cantidad < umbral,
            )
            .order_by(Producto.stock_cantidad)
        ).all()
        return [(int(r[0]), r[1], int(r[2])) for r in rows]

    # ── Ingresos por forma de pago ───────────────────────────────────

    def get_ingresos_por_forma_pago(self, desde: date, hasta: date) -> List[Tuple[str, Decimal, int]]:
        rows = self.session.execute(
            text(
                """
                SELECT
                    p.forma_pago_codigo,
                    COALESCE(SUM(p.total), 0) AS total,
                    COUNT(*)                  AS cantidad
                FROM pedidos p
                JOIN pagos pg ON pg.pedido_id = p.id
                WHERE p.deleted_at IS NULL
                  AND p.estado_codigo != 'CANCELADO'
                  AND pg.mp_status = 'approved'
                  AND p.created_at::date BETWEEN :desde AND :hasta
                GROUP BY p.forma_pago_codigo
                ORDER BY total DESC
                """
            ),
            {"desde": desde, "hasta": hasta},
        ).fetchall()
        return [(r[0], Decimal(str(r[1])), int(r[2])) for r in rows]
