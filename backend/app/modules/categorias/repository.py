# app/modules/categorias/repository.py
from typing import Optional, List
from sqlmodel import Session, select, func
from app.modules.categorias.models import Categoria
from app.core.repository import BaseRepository


class CategoriaRepository(BaseRepository[Categoria]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Categoria)

    def get_by_nombre(self, nombre: str) -> Optional[Categoria]:
        return self.session.exec(
            select(Categoria).where(Categoria.nombre == nombre)
        ).first()

    def get_all_activas(
        self,
        offset: int = 0,
        limit: int = 20,
        incluir_inactivos: bool = False,
        nombre: Optional[str] = None,
    ) -> List[Categoria]:
        q = select(Categoria)
        if not incluir_inactivos:
            q = q.where(Categoria.deleted_at == None)
        if nombre:
            q = q.where(Categoria.nombre.ilike(f"%{nombre}%"))
        q = q.order_by(Categoria.nombre).offset(offset).limit(limit)
        return list(self.session.exec(q).all())

    def count_activas(self, incluir_inactivos: bool = False, nombre: Optional[str] = None) -> int:
        q = select(func.count(Categoria.id))
        if not incluir_inactivos:
            q = q.where(Categoria.deleted_at == None)
        if nombre:
            q = q.where(Categoria.nombre.ilike(f"%{nombre}%"))
        return self.session.exec(q).one()

    def get_roots(self, incluir_inactivos: bool = False) -> List[Categoria]:
        q = select(Categoria).where(Categoria.parent_id == None)
        if not incluir_inactivos:
            q = q.where(Categoria.deleted_at == None)
        return list(self.session.exec(q).all())

    def count_roots(self, incluir_inactivos: bool = False) -> int:
        q = select(func.count(Categoria.id)).where(Categoria.parent_id == None)
        if not incluir_inactivos:
            q = q.where(Categoria.deleted_at == None)
        return self.session.exec(q).one()

    def get_children(self, parent_id: int, incluir_inactivos: bool = False) -> List[Categoria]:
        q = select(Categoria).where(Categoria.parent_id == parent_id)
        if not incluir_inactivos:
            q = q.where(Categoria.deleted_at == None)
        return list(self.session.exec(q).all())

    def get_descendientes_ids(self, categoria_id: int) -> list[int]:
        """
        Devuelve [categoria_id, ...todos sus descendientes activos e inactivos].
        Usada por aplicar_margen para resolver productos de una categoría
        y toda su jerarquía descendente (RN-PR09).
        """
        ids = [categoria_id]
        cola = [categoria_id]
        while cola:
            padre_id = cola.pop()
            hijos = list(self.session.exec(
                select(Categoria.id).where(Categoria.parent_id == padre_id)
            ).all())
            for h in hijos:
                ids.append(h)
                cola.append(h)
        return ids

    def count_productos_activos(self, categoria_id: int) -> int:
        """
        Cuenta productos activos (deleted_at IS NULL) asociados a esta categoría
        vía la tabla producto_categorias 
        """
        from app.modules.productos.models import Producto, ProductoCategoria

        q = (
            select(func.count(Producto.id))
            .join(ProductoCategoria, ProductoCategoria.producto_id == Producto.id)
            .where(
                ProductoCategoria.categoria_id == categoria_id,
                Producto.deleted_at == None,  # noqa: E711
            )
        )
        return self.session.exec(q).one()
