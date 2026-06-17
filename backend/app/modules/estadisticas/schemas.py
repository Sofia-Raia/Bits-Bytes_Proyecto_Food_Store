# app/modules/estadisticas/schemas.py
"""Schemas de solo lectura para el módulo de estadísticas."""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlmodel import SQLModel


class ProductoStockBajo(SQLModel):
    id: int
    nombre: str
    stock_cantidad: int


class ResumenResponse(SQLModel):
    ventas_hoy: Decimal
    ventas_mes: Decimal
    ticket_promedio: Decimal
    pedidos_activos: int
    productos_stock_bajo: List[ProductoStockBajo]


class VentasPeriodoItem(SQLModel):
    periodo: str
    total_ventas: Decimal
    cantidad_pedidos: int


class ProductoTopItem(SQLModel):
    producto_id: int
    nombre: str
    ingresos: Decimal
    cantidad_vendida: int


class PedidosEstadoItem(SQLModel):
    estado_codigo: str
    cantidad: int


class IngresosItem(SQLModel):
    forma_pago_codigo: str
    total: Decimal
    cantidad: int


class IngresosResponse(SQLModel):
    items: List[IngresosItem]
