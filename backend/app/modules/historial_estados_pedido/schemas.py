# app/modules/historial_estados_pedido/schemas.py
"""Schemas de lectura para HistorialEstadoPedido (T-B12)."""
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class HistorialPublic(SQLModel):
    """
    Representación pública de una entrada del historial.
    Solo se expone para lectura — los writes son internos al service de pedidos.
    """
    id: int
    pedido_id: int
    estado_desde: Optional[str]
    estado_hacia: str
    usuario_id: Optional[int]
    motivo: Optional[str]
    created_at: datetime
