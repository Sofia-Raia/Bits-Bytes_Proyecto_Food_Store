# app/modules/estadisticas/service.py
"""Service del módulo de estadísticas. Ensambla KPIs desde el repository."""
from datetime import date
from decimal import Decimal
from typing import List

from sqlmodel import Session

from app.modules.estadisticas.repository import EstadisticasRepository
from app.modules.estadisticas.schemas import (
    IngresosItem, IngresosResponse, PedidosEstadoItem,
    ProductoStockBajo, ProductoTopItem, ResumenResponse, VentasPeriodoItem,
)

_Q = Decimal("0.01")


class EstadisticasService:

    def __init__(self, session: Session) -> None:
        self._repo = EstadisticasRepository(session)

    def resumen(self) -> ResumenResponse:
        return ResumenResponse(
            ventas_hoy=self._repo.get_ventas_hoy().quantize(_Q),
            ventas_mes=self._repo.get_ventas_mes().quantize(_Q),
            ticket_promedio=self._repo.get_ticket_promedio().quantize(_Q),
            pedidos_activos=self._repo.get_pedidos_activos(),
            productos_stock_bajo=[
                ProductoStockBajo(id=pid, nombre=nombre, stock_cantidad=stock)
                for pid, nombre, stock in self._repo.get_stock_bajo()
            ],
        )

    def ventas_periodo(self, desde: date, hasta: date, agrupacion: str) -> List[VentasPeriodoItem]:
        return [
            VentasPeriodoItem(
                periodo=periodo,
                total_ventas=total.quantize(_Q),
                cantidad_pedidos=cant,
            )
            for periodo, total, cant in self._repo.get_ventas_periodo(desde, hasta, agrupacion)
        ]

    def productos_top(self, limit: int) -> List[ProductoTopItem]:
        return [
            ProductoTopItem(
                producto_id=pid,
                nombre=nombre,
                ingresos=ingresos.quantize(_Q),
                cantidad_vendida=cant,
            )
            for pid, nombre, ingresos, cant in self._repo.get_productos_top(limit)
        ]

    def pedidos_por_estado(self) -> List[PedidosEstadoItem]:
        return [
            PedidosEstadoItem(estado_codigo=estado, cantidad=cant)
            for estado, cant in self._repo.get_pedidos_por_estado()
        ]

    def ingresos_por_forma_pago(self, desde: date, hasta: date) -> IngresosResponse:
        items = [
            IngresosItem(
                forma_pago_codigo=fp,
                total=total.quantize(_Q),
                cantidad=cant,
            )
            for fp, total, cant in self._repo.get_ingresos_por_forma_pago(desde, hasta)
        ]
        return IngresosResponse(items=items)
