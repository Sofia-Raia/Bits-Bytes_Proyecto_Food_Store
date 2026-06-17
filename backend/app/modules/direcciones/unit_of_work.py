# app/modules/direcciones/unit_of_work.py
"""
UnitOfWork del módulo direcciones.

"""
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.direcciones.repository import DireccionRepository


class DireccionUnitOfWork(UnitOfWork):
    """UoW del módulo direcciones. Expone self.direcciones."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.direcciones = DireccionRepository(session)
