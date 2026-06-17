# app/modules/productos/unit_of_work.py
"""UnitOfWork del módulo productos."""
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.productos.repository import (
    CategoriaRefRepository,
    IngredienteRefRepository,
    ProductoRepository,
)


class ProductoUnitOfWork(UnitOfWork):
    """
    UoW del módulo productos.

    Expone:
    - productos:    CRUD de Producto, ProductoCategoria, ProductoIngrediente.
    - categorias:   lectura de Categoria (para validar ids y resolver árbol en margen).
    - ingredientes: lectura de Ingrediente (para calcular precio_costo on-the-fly).
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.productos    = ProductoRepository(session)
        self.categorias   = CategoriaRefRepository(session)
        self.ingredientes = IngredienteRefRepository(session)
