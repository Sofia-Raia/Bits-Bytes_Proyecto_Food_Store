# app/modules/ingredientes/repository.py
from typing import Optional, List
from sqlmodel import Session, select, func, asc, desc
from app.modules.ingredientes.models import Ingrediente, UnidadMedida
from app.core.repository import BaseRepository

_SORT_COLUMNS = {
    'nombre':      Ingrediente.nombre,
    'codigo':      Ingrediente.codigo,
    'es_alergeno': Ingrediente.es_alergeno,
    'created_at':  Ingrediente.created_at,
}


class IngredienteRepository(BaseRepository[Ingrediente]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Ingrediente)

    def get_by_id_for_update(self, id_: int) -> Optional[Ingrediente]:
        """
        SELECT ... FOR UPDATE — lock pesimista sobre la fila.
        Evita race conditions al validar/decrementar stock de ingredientes.
        Debe ejecutarse dentro de una transacción activa (UoW).
        """
        stmt = select(Ingrediente).where(Ingrediente.id == id_).with_for_update()
        return self.session.exec(stmt).first()

    def get_by_nombre(self, nombre: str) -> Optional[Ingrediente]:
        return self.session.exec(
            select(Ingrediente).where(Ingrediente.nombre == nombre)
        ).first()

    # ── Catálogo UnidadMedida (lookups; el catálogo no tiene módulo propio) ────

    def get_unidad_by_codigo(self, codigo: str) -> Optional[UnidadMedida]:
        return self.session.exec(
            select(UnidadMedida).where(UnidadMedida.codigo == codigo)
        ).first()

    def get_unidad_by_id(self, unidad_id: int) -> Optional[UnidadMedida]:
        return self.session.get(UnidadMedida, unidad_id)

    def list_unidades(self) -> List[UnidadMedida]:
        return list(
            self.session.exec(select(UnidadMedida).order_by(UnidadMedida.id)).all()
        )

    def get_all_paginado(
        self,
        offset: int = 0,
        limit: int = 20,
        incluir_inactivos: bool = False,
        nombre: Optional[str] = None,
        sort_by: str = 'nombre',
        sort_dir: str = 'asc',
    ) -> List[Ingrediente]:
        q = select(Ingrediente)
        if not incluir_inactivos:
            q = q.where(Ingrediente.deleted_at == None)
        if nombre:
            q = q.where(Ingrediente.nombre.ilike(f"%{nombre}%"))
        col = _SORT_COLUMNS.get(sort_by, Ingrediente.nombre)
        order = asc(col) if sort_dir == 'asc' else desc(col)
        q = q.order_by(order).offset(offset).limit(limit)
        return list(self.session.exec(q).all())

    def count(self, incluir_inactivos: bool = False, nombre: Optional[str] = None) -> int:
        q = select(func.count(Ingrediente.id))
        if not incluir_inactivos:
            q = q.where(Ingrediente.deleted_at == None)
        if nombre:
            q = q.where(Ingrediente.nombre.ilike(f"%{nombre}%"))
        return self.session.exec(q).one()
