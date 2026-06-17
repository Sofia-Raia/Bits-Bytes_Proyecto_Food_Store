# app/modules/pedidos/schemas.py
"""
Schemas del módulo pedidos.

Decimal:
- Todos los campos monetarios usan MoneyDecimal para precisión y serialización
  correcta como float en JSON.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import Field
from sqlmodel import SQLModel

from app.core.types import MoneyDecimal

# Re-exportado para que router.py no cambie sus imports 
from app.modules.historial_estados_pedido.schemas import HistorialPublic  

class FormaPagoPublic(SQLModel):
    codigo: str
    descripcion: str
    habilitado: bool


class PedidoConfigPublic(SQLModel):
    """Parámetros públicos del checkout. costo_envio es el cargo fijo que el
    backend aplica al total (lo que cobra MercadoPago)."""
    costo_envio: MoneyDecimal


class EstadoPedidoPublic(SQLModel):
    codigo: str
    descripcion: str
    orden: int
    es_terminal: bool


class ItemPedidoRequest(SQLModel):
    producto_id: int
    cantidad: int = Field(ge=1)
    personalizacion: Optional[List[int]] = None


class DetallePedidoPublic(SQLModel):
    pedido_id: int
    producto_id: int
    cantidad: int
    nombre_snapshot: str
    precio_snapshot: MoneyDecimal
    subtotal_snap:   MoneyDecimal
    personalizacion: Optional[List[int]] = None
    created_at: datetime


class PedidoCreate(SQLModel):
    """
    Body para crear un pedido.

    - usuario_id: Optional — solo honrado si el caller tiene rol ADMIN o PEDIDOS
      (opción c, T-B32). Si el caller es CLIENT, se ignora y se usa el del JWT.
      Si un CLIENT envía usuario_id distinto al suyo → 403 en router.
    - descuento: calculado por el servidor (Versión B = 0.00). No se acepta del body.
    - costo_envio: calculado por el servidor (50.00 si hay direccion_id, 0.00 si retiro).
    """
    forma_pago_codigo: str = Field(max_length=20)
    direccion_id: Optional[int] = None
    notas: Optional[str] = None
    items: List[ItemPedidoRequest] = Field(min_length=1)
    # solo aceptado si caller tiene ADMIN o PEDIDOS
    usuario_id: Optional[int] = None


class PedidoUpdate(SQLModel):
    """
    Body para editar un pedido PENDIENTE (T4 / D5).
    - items: si se envía, reemplaza todos los ítems del pedido.
    - forma_pago_codigo: cambia la forma de pago.
    - direccion_id: cambia la dirección (regenera snapshot).
    - notas: cambia las notas.
    usuario_id, descuento y costo_envio son inmutables desde el body.
    """
    forma_pago_codigo: Optional[str] = Field(default=None, max_length=20)
    # TODO(contrato): direccion_id no distingue "no cambiar" de "pasar a retiro (null)".
    # Con Optional[int]=None ambos casos colapsan en None, por lo que hoy no se puede
    # convertir un pedido de delivery a retiro vía PATCH. Requiere decidir un mecanismo
    # explícito (flag quitar_direccion o valor sentinel) antes de cambiar el contrato.
    direccion_id: Optional[int] = None
    notas: Optional[str] = None
    items: Optional[List[ItemPedidoRequest]] = None


class AvanzarEstadoRequest(SQLModel):
    """
    Body para avanzar el estado de un pedido.
    usuario_id ELIMINADO — siempre se toma del JWT.
    motivo requerido si el estado destino es CANCELADO o PENDIENTE→CONFIRMADO manual.
    """
    estado_hacia: str = Field(max_length=20)
    motivo: Optional[str] = None


class PedidoPublic(SQLModel):
    id: int
    codigo: str
    usuario_id: int
    usuario_nombre: Optional[str] = None
    direccion_id: Optional[int] = None
    # snapshot JSON de la dirección al crear el pedido (None si retiro en local)
    direccion_snapshot: Optional[str] = None
    estado_codigo: str
    forma_pago_codigo: str
    subtotal:    MoneyDecimal
    descuento:   MoneyDecimal
    costo_envio: MoneyDecimal
    total:       MoneyDecimal
    notas: Optional[str] = None
    detalles: List[DetallePedidoPublic] = []
    historial: List[HistorialPublic] = []
    created_at: datetime
    updated_at: datetime
    


class PedidoList(SQLModel):
    data: List[PedidoPublic]
    total: int
