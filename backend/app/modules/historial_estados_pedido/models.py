# app/modules/historial_estados_pedido/models.py
"""
Modelo HistorialEstadoPedido — movido desde pedidos/models.py .

Nota de diseño: NO se define Relationship back a Pedido para evitar
el ciclo de importación historial→pedidos→historial. El acceso se hace
siempre desde Pedido.historial (sentido único, suficiente para todos
los casos de uso del módulo). La FK pedido_id es suficiente para queries.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class HistorialEstadoPedido(SQLModel, table=True):
    """
    Registro append-only de cada cambio de estado de un pedido.
    RN-DA05 / RN-FS07: nunca se actualiza ni elimina una entrada.
    Los INSERT los hace únicamente el PedidoService vía uow.historial.add().
    """
    __tablename__ = "historial_estados_pedido"

    id: Optional[int] = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedidos.id", ondelete="CASCADE", nullable=False, index=True)
    estado_desde: Optional[str] = Field(
        default=None, foreign_key="estados_pedido.codigo", max_length=20
    )
    estado_hacia: str = Field(foreign_key="estados_pedido.codigo", max_length=20, nullable=False)
    usuario_id: Optional[int] = Field(default=None)
    motivo: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
