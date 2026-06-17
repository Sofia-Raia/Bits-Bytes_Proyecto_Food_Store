# app/modules/pagos/unit_of_work.py
"""
UnitOfWork del módulo pagos.

Expone:
- pagos:   operaciones sobre Pago.

La confirmación del pedido (decremento de stock + historial) la maneja
PedidoService.confirmar_por_pago con su propia UoW; este UoW solo persiste el Pago.
"""
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.pagos.repository import PagoRepository


class PagoUnitOfWork(UnitOfWork):
    """UoW del módulo pagos. Expone self.pagos."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.pagos = PagoRepository(session)
