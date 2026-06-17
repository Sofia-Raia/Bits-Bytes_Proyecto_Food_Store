# app/modules/productos/repository.py

from typing import List, Optional

from sqlalchemy import delete as sa_delete
from sqlmodel import Session, asc, desc, func, select

from app.core.repository import BaseRepository
from app.modules.categorias.models import Categoria
from app.modules.ingredientes.models import Ingrediente
from app.modules.productos.models import Producto, ProductoCategoria, ProductoIngrediente

_SORT_COLUMNS = {
    "nombre":         Producto.nombre,
    "codigo":         Producto.codigo,
    "precio_base":    Producto.precio_base,
    "stock_cantidad": Producto.stock_cantidad,
    "created_at":     Producto.created_at,
}


class ProductoRepository(BaseRepository[Producto]):

    def get_by_id(self, id_: int) -> Optional[Producto]:
        return self.session.get(Producto, id_)

    def get_by_id_for_update(self, id_: int) -> Optional[Producto]:
        """
        SELECT ... FOR UPDATE — lock pesimista sobre la fila.
        Evita race conditions al validar/decrementar stock concurrentemente .
        Debe ejecutarse dentro de una transacción activa (UoW).
        """
        stmt = select(Producto).where(Producto.id == id_).with_for_update()
        return self.session.exec(stmt).first()

    def get_by_nombre_exacto(self, nombre: str) -> Optional[Producto]:
        """Match exacto por nombre (case-sensitive). Usado para validar unicidad."""
        return self.session.exec(
            select(Producto).where(Producto.nombre == nombre)
        ).first()

    def get_all_activos(
        self,
        offset: int = 0,
        limit: int = 20,
        incluir_inactivos: bool = False,
        nombre: Optional[str] = None,
        categoria_id: Optional[int] = None,
        sort_by: str = "nombre",
        sort_dir: str = "asc",
    ) -> List[Producto]:
        q = select(Producto)
        if categoria_id is not None:
            q = q.join(
                ProductoCategoria, ProductoCategoria.producto_id == Producto.id
            ).where(ProductoCategoria.categoria_id == categoria_id)
        if not incluir_inactivos:
            q = q.where(Producto.deleted_at == None)  
        if nombre:
            q = q.where(Producto.nombre.ilike(f"%{nombre}%"))
        col = _SORT_COLUMNS.get(sort_by, Producto.nombre)
        order = asc(col) if sort_dir == "asc" else desc(col)
        q = q.order_by(order).offset(offset).limit(limit)
        return list(self.session.exec(q).all())

    def count_activos(
        self,
        incluir_inactivos: bool = False,
        nombre: Optional[str] = None,
        categoria_id: Optional[int] = None,
    ) -> int:
        q = select(func.count(Producto.id))
        if categoria_id is not None:
            q = q.join(
                ProductoCategoria, ProductoCategoria.producto_id == Producto.id
            ).where(ProductoCategoria.categoria_id == categoria_id)
        if not incluir_inactivos:
            q = q.where(Producto.deleted_at == None)  
        if nombre:
            q = q.where(Producto.nombre.ilike(f"%{nombre}%"))
        return self.session.exec(q).one()

    def get_producto_categorias(self, producto_id: int) -> List[ProductoCategoria]:
        return list(self.session.exec(
            select(ProductoCategoria).where(ProductoCategoria.producto_id == producto_id)
        ).all())

    def get_producto_ingredientes(self, producto_id: int) -> List[ProductoIngrediente]:
        return list(self.session.exec(
            select(ProductoIngrediente).where(ProductoIngrediente.producto_id == producto_id)
        ).all())

    def add(self, obj: Producto) -> Producto:
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)
        return obj

    def add_link(self, obj) -> None:
        self.session.add(obj)
        self.session.flush()

    def delete_categorias(self, producto_id: int) -> None:
        self.session.execute(
            sa_delete(ProductoCategoria).where(ProductoCategoria.producto_id == producto_id)
        )
        self.session.flush()

    def delete_ingredientes(self, producto_id: int) -> None:
        self.session.execute(
            sa_delete(ProductoIngrediente).where(ProductoIngrediente.producto_id == producto_id)
        )
        self.session.flush()

    def get_by_categoria_ids(self, categoria_ids: list[int]) -> list[Producto]:
        """
        Devuelve todos los productos activos asociados a cualquiera de las
        categorías indicadas. Usado por aplicar_margen scope=categoria.
        """
        if not categoria_ids:
            return []
        stmt = (
            select(Producto)
            .join(ProductoCategoria, ProductoCategoria.producto_id == Producto.id)
            .where(
                ProductoCategoria.categoria_id.in_(categoria_ids),
                Producto.deleted_at == None,  # noqa: E711
            )
            .distinct()
        )
        return list(self.session.exec(stmt).all())


class CategoriaRefRepository(BaseRepository[Categoria]):
    def get_by_id(self, id_: int) -> Optional[Categoria]:
        return self.session.get(Categoria, id_)


class IngredienteRefRepository(BaseRepository[Ingrediente]):
    def get_by_id(self, id_: int) -> Optional[Ingrediente]:
        return self.session.get(Ingrediente, id_)
