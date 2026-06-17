# app/modules/categorias/models.py
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import relationship as sa_rel
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.modules.productos.models import ProductoCategoria


class Categoria(SQLModel, table=True):
    """
    Árbol recursivo auto-referencial.
    Borrado lógico: deleted_at — activo es @property derivada.
    Código (CAT-NNNN) inmutable.
    """
    __tablename__ = "categorias"

    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(max_length=20, unique=True, index=True)
    parent_id: Optional[int] = Field(default=None, foreign_key="categorias.id", nullable=True)
    nombre: str = Field(min_length=2, max_length=100, unique=True, index=True)
    descripcion: Optional[str] = Field(default=None)
    imagen_url: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)

    @property
    def activo(self) -> bool:
        return self.deleted_at is None

    parent: Optional["Categoria"] = Relationship(
        sa_relationship=sa_rel(
            "Categoria",
            foreign_keys="[Categoria.parent_id]",
            back_populates="subcategorias",
            remote_side="[Categoria.id]",
            lazy="selectin",
            uselist=False,
        )
    )

    subcategorias: List["Categoria"] = Relationship(
        sa_relationship=sa_rel(
            "Categoria",
            foreign_keys="[Categoria.parent_id]",
            back_populates="parent",
            lazy="selectin",
        )
    )

    producto_categorias: List["ProductoCategoria"] = Relationship(
        back_populates="categoria"
    )
