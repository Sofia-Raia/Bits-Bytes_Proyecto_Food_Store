# app/modules/pagos/repository.py
"""
Repositorio del módulo pagos .

Firma de BaseRepository: __init__(self, session, model) — sesión primero.
Lecturas para localizar el Pago por pedido, por idempotencia o por los
identificadores que devuelve MercadoPago (payment_id / merchant_order_id).
"""
from typing import List, Optional

from sqlmodel import Session, select

from app.core.repository import BaseRepository
from app.modules.pagos.models import Pago


class PagoRepository(BaseRepository[Pago]):
    """Repositorio del módulo pagos."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Pago)

    def get_by_pedido(self, pedido_id: int) -> List[Pago]:
        """Todos los pagos asociados a un pedido (orden ascendente por id)."""
        return list(
            self.session.exec(
                select(Pago).where(Pago.pedido_id == pedido_id).order_by(Pago.id)
            ).all()
        )

    def get_ultimo_by_pedido(self, pedido_id: int) -> Optional[Pago]:
        """Último intento de pago de un pedido (mayor id)."""
        return self.session.exec(
            select(Pago)
            .where(Pago.pedido_id == pedido_id)
            .order_by(Pago.id.desc())  # type: ignore[attr-defined]
        ).first()

    def get_by_idempotency_key(self, key: str) -> Optional[Pago]:
        return self.session.exec(
            select(Pago).where(Pago.idempotency_key == key)
        ).first()

    def get_by_external_reference(self, external_reference: str) -> Optional[Pago]:
        return self.session.exec(
            select(Pago).where(Pago.external_reference == external_reference)
        ).first()

    def get_by_mp_payment_id(self, payment_id: int) -> Optional[Pago]:
        return self.session.exec(
            select(Pago).where(Pago.mp_payment_id == payment_id)
        ).first()

    def get_by_mp_merchant_order_id(self, merchant_order_id: int) -> Optional[Pago]:
        return self.session.exec(
            select(Pago).where(Pago.mp_merchant_order_id == merchant_order_id)
        ).first()
