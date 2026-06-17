# app/modules/historial_estados_pedido/service.py
"""
Service de solo lectura para HistorialEstadoPedido.

IMPORTANTE: NO existe método público crear() / add().
Los INSERT los realiza el PedidoService vía uow.historial.add() para garantizar
que la inserción quede dentro de la misma transacción que el cambio de estado.
"""
from sqlmodel import Session

from app.modules.historial_estados_pedido.repository import HistorialRepository
from app.modules.historial_estados_pedido.schemas import HistorialPublic
from app.modules.historial_estados_pedido.unit_of_work import HistorialUnitOfWork


class HistorialService:

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_pedido(self, pedido_id: int) -> list[HistorialPublic]:
        """
        Devuelve el historial de estados de un pedido, ordenado ASC por fecha.
        Consumido desde el router de pedidos en GET /pedidos/{id}/historial.
        """
        with HistorialUnitOfWork(self._session) as uow:
            entradas = uow.repo.get_by_pedido(pedido_id)
            return [HistorialPublic.model_validate(e) for e in entradas]
