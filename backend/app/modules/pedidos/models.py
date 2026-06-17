# app/modules/pedidos/models.py
"""
Modelos del módulo pedidos.

Sprint 5:
- HistorialEstadoPedido movido a historial_estados_pedido/models.py.
- usuario_id NOT NULL: siempre llega del JWT via service .

Sprint 6 — T-B31:
- Pedido.direccion_snapshot: TEXT opcional. JSON con datos textuales de la
  dirección al crear el pedido (snapshot inmutable).

Decimal:
- subtotal, descuento, costo_envio, total → NUMERIC(12,2).
- precio_snapshot, subtotal_snap en DetallePedido → NUMERIC(12,2).
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import ARRAY, Column, Integer, Numeric, SmallInteger
from sqlmodel import Field, Relationship, SQLModel

from app.modules.historial_estados_pedido.models import HistorialEstadoPedido  


class FormaPago(SQLModel, table=True):
    __tablename__ = "formas_pago"
    codigo: str = Field(max_length=20, primary_key=True)
    descripcion: str = Field(max_length=80)
    habilitado: bool = Field(default=True)
    pedidos: List["Pedido"] = Relationship(back_populates="forma_pago")


class EstadoPedido(SQLModel, table=True):
    __tablename__ = "estados_pedido"
    codigo: str = Field(max_length=20, primary_key=True)
    descripcion: str = Field(max_length=80)
    orden: int = Field()
    es_terminal: bool = Field(default=False)
    pedidos: List["Pedido"] = Relationship(back_populates="estado")


class Pedido(SQLModel, table=True):
    """
    Código (PED-NNNN) inmutable.
    usuario_id NOT NULL: proviene siempre del JWT (T-B08 / T-B32).
    direccion_snapshot: JSON con datos de la dirección al crear (T-B31 / RN-PE03).
    Borrado lógico via deleted_at.

    Campos monetarios en NUMERIC(12,2) para precisión decimal.
    """
    __tablename__ = "pedidos"

    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(max_length=20, unique=True, index=True)
    usuario_id: int = Field(nullable=False, index=True)
    direccion_id: Optional[int] = Field(default=None)
    direccion_snapshot: Optional[str] = Field(default=None)

    estado_codigo: str = Field(
        default="PENDIENTE", foreign_key="estados_pedido.codigo", max_length=20
    )
    forma_pago_codigo: str = Field(foreign_key="formas_pago.codigo", max_length=20)

    subtotal:    Decimal = Field(ge=0, sa_column=Column(Numeric(12, 2), nullable=False))
    descuento:   Decimal = Field(default=Decimal("0.00"), ge=0, sa_column=Column(Numeric(12, 2), nullable=False))
    costo_envio: Decimal = Field(default=Decimal("0.00"), ge=0, sa_column=Column(Numeric(12, 2), nullable=False))
    total:       Decimal = Field(ge=0, sa_column=Column(Numeric(12, 2), nullable=False))

    notas: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)

    estado:     Optional[EstadoPedido] = Relationship(back_populates="pedidos")
    forma_pago: Optional[FormaPago]    = Relationship(back_populates="pedidos")
    detalles:   List["DetallePedido"]  = Relationship(back_populates="pedido")
    historial:  List[HistorialEstadoPedido] = Relationship()


class DetallePedido(SQLModel, table=True):
    __tablename__ = "detalle_pedidos"

    pedido_id:   int = Field(foreign_key="pedidos.id",   primary_key=True, ondelete="CASCADE")
    producto_id: int = Field(foreign_key="productos.id", primary_key=True, ondelete="RESTRICT")
    cantidad:    int = Field(ge=1, sa_column=Column(SmallInteger, nullable=False))
    nombre_snapshot: str = Field(max_length=200)

    # Snapshots de precio — NUMERIC(12,2) para precisión
    precio_snapshot: Decimal = Field(ge=0, sa_column=Column(Numeric(12, 2), nullable=False))
    subtotal_snap:   Decimal = Field(ge=0, sa_column=Column(Numeric(12, 2), nullable=False))

    personalizacion: Optional[List[int]] = Field(
        default=None, sa_column=Column(ARRAY(Integer), nullable=True)
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    pedido: Optional[Pedido] = Relationship(back_populates="detalles")
