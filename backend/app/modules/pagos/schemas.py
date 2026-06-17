# app/modules/pagos/schemas.py
"""
Schemas (DTOs) del módulo pagos.

- CrearPagoRequest:    body de POST /create-preference.
- ConfirmarPagoRequest: body de POST /confirm (refresco desde la página de resultado).
- PagoCrearResponse:   respuesta al crear la preferencia (incluye init_point para redirect).
- PagoEstadoResponse:  estado actual del pago de un pedido.
"""
from typing import Optional

from sqlmodel import SQLModel


class CrearPagoRequest(SQLModel):
    """Body para crear la preferencia de pago de un pedido."""
    pedido_id: int


class ConfirmarPagoRequest(SQLModel):
    """Body para refrescar/confirmar el estado del pago tras el redirect."""
    pedido_id: int
    payment_id: Optional[int] = None


class PagoCrearResponse(SQLModel):
    """Respuesta de POST /create-preference."""
    pago_id: int
    preference_id: str
    init_point: Optional[str] = None
    public_key: Optional[str] = None


class PagoEstadoResponse(SQLModel):
    """Estado del pago de un pedido (interno: pendiente|aprobado|rechazado)."""
    estado: Optional[str] = None
    pedido_id: int
