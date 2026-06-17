# app/modules/historial_estados_pedido/repository.py
"""
Repositorio append-only para HistorialEstadoPedido.

Reglas de negocio:
- RN-DA05 / RN-FS07: el historial NUNCA se modifica ni elimina.
- delete() sobrescrito con NotImplementedError para hacer explícita la restricción.
- Los INSERT se realizan desde PedidoUnitOfWork (misma sesión → misma transacción),
  no directamente desde este repositorio en producción.
"""
from sqlmodel import Session, select

from app.core.repository import BaseRepository
from app.modules.historial_estados_pedido.models import HistorialEstadoPedido


class HistorialRepository(BaseRepository[HistorialEstadoPedido]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, HistorialEstadoPedido)

    # ── Escritura ─────────────────────────────────────────────────────────────

    def add(self, entrada: HistorialEstadoPedido) -> HistorialEstadoPedido:
        """Append-only INSERT. El UoW hace el commit."""
        self.session.add(entrada)
        self.session.flush()
        return entrada

    def delete(self, instance: HistorialEstadoPedido) -> None:  # type: ignore[override]
        """
        Prohibido. El historial es append-only (RN-DA05).
        Sobrescrito explícitamente para que cualquier llamada accidental falle rápido.
        """
        raise NotImplementedError(
            "HistorialEstadoPedido es append-only — no se puede eliminar (RN-DA05 / RN-FS07)."
        )

    # ── Lectura ───────────────────────────────────────────────────────────────

    def get_by_pedido(self, pedido_id: int) -> list[HistorialEstadoPedido]:
        """Devuelve el historial de un pedido ordenado ASC por fecha de creación."""
        return list(
            self.session.exec(
                select(HistorialEstadoPedido)
                .where(HistorialEstadoPedido.pedido_id == pedido_id)
                .order_by(HistorialEstadoPedido.created_at.asc())
            ).all()
        )
