# app/modules/historial_estados_pedido/unit_of_work.py
"""
UnitOfWork standalone para HistorialService (T-B12).

NOTA DE DISEÑO: Este UoW NO se usa en el flujo de pedidos.
Los INSERT de historial en ese contexto pasan por PedidoUnitOfWork.historial
(misma sesión → misma transacción que el cambio de estado del pedido).
Este UoW existe para que HistorialService pueda usarse de forma independiente
(e.g. endpoint GET /historial/pedido/{id} si se expone en el futuro).
"""
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.historial_estados_pedido.repository import HistorialRepository


class HistorialUnitOfWork(UnitOfWork):

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.repo = HistorialRepository(session)
