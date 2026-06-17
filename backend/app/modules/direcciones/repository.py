# app/modules/direcciones/repository.py
"""
Repository del módulo direcciones.

Sprint 6 — T-B30.
"""
from typing import List, Optional

from sqlmodel import Session, func, select

from app.core.repository import BaseRepository
from app.modules.direcciones.models import DireccionEntrega


class DireccionRepository(BaseRepository[DireccionEntrega]):
    """
    Acceso a datos de DireccionEntrega.

    Todos los métodos filtran por deleted_at IS NULL salvo los de admin.
    La separación de ownership se delega al service (más legible).
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session, DireccionEntrega)

    # ── Lectura ───────────────────────────────────────────────────────────────

    def get_by_id_activa(self, id_: int) -> Optional[DireccionEntrega]:
        """Devuelve una dirección activa por id, sin filtro de usuario (para ADMIN)."""
        return self.session.exec(
            select(DireccionEntrega).where(
                DireccionEntrega.id == id_,
                DireccionEntrega.deleted_at == None,  # noqa: E711
            )
        ).first()

    def get_by_id_y_usuario(
        self, id_: int, usuario_id: int
    ) -> Optional[DireccionEntrega]:
        """Devuelve una dirección activa filtrando por usuario (ownership para CLIENT)."""
        return self.session.exec(
            select(DireccionEntrega).where(
                DireccionEntrega.id == id_,
                DireccionEntrega.usuario_id == usuario_id,
                DireccionEntrega.deleted_at == None,  # noqa: E711
            )
        ).first()

    def get_all_by_usuario(
        self, usuario_id: int, offset: int = 0, limit: int = 20
    ) -> List[DireccionEntrega]:
        return list(self.session.exec(
            select(DireccionEntrega)
            .where(
                DireccionEntrega.usuario_id == usuario_id,
                DireccionEntrega.deleted_at == None,  # noqa: E711
            )
            .order_by(DireccionEntrega.es_principal.desc(), DireccionEntrega.created_at)
            .offset(offset)
            .limit(limit)
        ).all())

    def count_by_usuario(self, usuario_id: int) -> int:
        return self.session.exec(
            select(func.count(DireccionEntrega.id)).where(
                DireccionEntrega.usuario_id == usuario_id,
                DireccionEntrega.deleted_at == None,  # noqa: E711
            )
        ).one()

    def get_all_admin(
        self,
        offset: int = 0,
        limit: int = 20,
        usuario_id: Optional[int] = None,
    ) -> List[DireccionEntrega]:
        q = select(DireccionEntrega).where(DireccionEntrega.deleted_at == None)  # noqa: E711
        if usuario_id is not None:
            q = q.where(DireccionEntrega.usuario_id == usuario_id)
        q = q.order_by(DireccionEntrega.usuario_id, DireccionEntrega.es_principal.desc()).offset(offset).limit(limit)
        return list(self.session.exec(q).all())

    def count_admin(self, usuario_id: Optional[int] = None) -> int:
        q = select(func.count(DireccionEntrega.id)).where(DireccionEntrega.deleted_at == None)  # noqa: E711
        if usuario_id is not None:
            q = q.where(DireccionEntrega.usuario_id == usuario_id)
        return self.session.exec(q).one()

    def count_activas_usuario(self, usuario_id: int) -> int:
        """Cuenta cuántas direcciones activas tiene el usuario (para auto-principal)."""
        return self.session.exec(
            select(func.count(DireccionEntrega.id)).where(
                DireccionEntrega.usuario_id == usuario_id,
                DireccionEntrega.deleted_at == None,  # noqa: E711
            )
        ).one()

    # ── Escritura ─────────────────────────────────────────────────────────────

    def add(self, obj: DireccionEntrega) -> DireccionEntrega:
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)
        return obj

    def desmarcar_principal(self, usuario_id: int) -> None:
        """
        Desmarca como principal todas las direcciones activas del usuario.
        Se llama justo antes de marcar una nueva dirección como principal,
        garantizando que solo haya una principal por usuario (RN-DI02).
        """
        actuales = list(self.session.exec(
            select(DireccionEntrega).where(
                DireccionEntrega.usuario_id == usuario_id,
                DireccionEntrega.es_principal == True,  # noqa: E712
                DireccionEntrega.deleted_at == None,     # noqa: E711
            )
        ).all())
        for d in actuales:
            d.es_principal = False
            self.session.add(d)
        self.session.flush()
