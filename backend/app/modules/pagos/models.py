# app/modules/pagos/models.py
"""
Modelo de dominio para pagos con MercadoPago.

- Pago: registro de un intento de pago de un pedido vía MercadoPago Checkout Pro.
  * monto en Decimal (NUMERIC(12,2)) — nunca float.
  * estado interno propio ("pendiente" | "aprobado" | "rechazado"), en paralelo
    al estado del Pedido (FSM). Un pago aprobado dispara la confirmación del pedido.
  * Campos mp_* guardan la información que devuelve MercadoPago (preferencia, pago,
    merchant order y detalle de estado) para trazabilidad y conciliación.
  * idempotency_key (unique) evita procesar dos veces el mismo intento.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Column, Numeric
from sqlmodel import Field, SQLModel


class Pago(SQLModel, table=True):
    """
    Pago de un pedido vía MercadoPago.

    El estado del pago es independiente del estado del pedido: el webhook de MP
    actualiza este registro y, si queda "aprobado", confirma el pedido como
    acción de sistema (confirmar_por_pago).
    """

    __tablename__ = "pagos"

    id: Optional[int] = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedidos.id", nullable=False, index=True)

    # Monto cobrado (snapshot del total del pedido al crear la preferencia)
    monto: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    # transaction_amount: monto efectivamente cobrado por MercadoPago.
    # Puede diferir de `monto` si MP aplica ajustes; se setea al confirmar el pago.
    transaction_amount: Optional[Decimal] = Field(
        default=None, sa_column=Column(Numeric(12, 2), nullable=True)
    )

    # Estado interno del pago: "pendiente" | "aprobado" | "rechazado"
    estado: str = Field(default="pendiente", max_length=20, nullable=False, index=True)

    # external_reference: referencia que viaja a MP para vincular el pago al pedido.
    external_reference: Optional[str] = Field(
        default=None, max_length=100, unique=True, index=True
    )

    # ── Datos devueltos por MercadoPago ──────────────────────────────────────
    mp_preference_id: Optional[str] = Field(default=None, max_length=120)
    mp_init_point: Optional[str] = Field(default=None, max_length=500)
    # payment_id y merchant_order_id de MP son enteros grandes → BigInteger
    # mp_payment_id es único (ERD v7): un pago de MP se registra una sola vez.
    mp_payment_id: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger, nullable=True, unique=True, index=True)
    )
    mp_merchant_order_id: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger, nullable=True, index=True)
    )
    mp_status: Optional[str] = Field(default=None, max_length=40)
    mp_status_detail: Optional[str] = Field(default=None, max_length=120)
    # payment_method_id: medio usado (visa, master, account_money, ...) 
    payment_method_id: Optional[str] = Field(default=None, max_length=50)

    # Clave de idempotencia generada al crear el intento de pago
    idempotency_key: str = Field(max_length=64, nullable=False, unique=True, index=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
