# app/modules/ingredientes/models.py
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, Numeric
from sqlmodel import SQLModel, Field, Relationship

from app.core.types import MoneyDecimal  # noqa: F401 – re-exportado implícitamente

if TYPE_CHECKING:
    from app.modules.productos.models import ProductoIngrediente


class UnidadMedida(SQLModel, table=True):
    """
    Catálogo de unidades de medida (ERD «Catalog»).

    Tabla de referencia sembrada por seed.py — NO tiene módulo propio (regla del
    profesor): vive dentro del módulo `ingredientes`, que es su dueño principal,
    y se expone vía un único endpoint de solo-lectura (GET /ingredientes/unidades-medida).

    - codigo:  clave semántica estable usada en la API (KG, L, UNIDADES, ...).
    - simbolo: representación corta para UI ("kg", "L", "u", ...).
    - tipo:    agrupación (MASA | VOLUMEN | UNIDAD | AREA) — filtra/agrupa en admin.
    """
    __tablename__ = "unidades_medida"

    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(max_length=20, unique=True, index=True)
    nombre: str = Field(max_length=50, unique=True)
    simbolo: str = Field(max_length=10, unique=True)
    tipo: str = Field(max_length=20)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Ingrediente(SQLModel, table=True):
    """
    Catálogo de ingredientes con stock propio (D1).
    Borrado lógico: deleted_at — activo es @property derivada.
    El código (INGR-NNNN) es inmutable y se genera al crear.

    costo: Decimal — costo por unidad de medida. NUMERIC(12,4) (RN-IN01).
    stock_cantidad: Decimal — stock disponible. NUMERIC(10,3). Permite fracciones.
    unidad_medida_id: FK → unidades_medida.id (RN-IN02). Reemplaza el enum anterior
        para cumplir el ERD (UnidadMedida como tabla catálogo).
    """
    __tablename__ = "ingredientes"
    __table_args__ = (
        CheckConstraint("stock_cantidad >= 0", name="ck_ingredientes_stock_nn"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(max_length=20, unique=True, index=True)
    nombre: str = Field(min_length=2, max_length=100, unique=True, index=True)
    descripcion: Optional[str] = Field(default=None)
    es_alergeno: bool = Field(default=False)

    # RN-IN01: costo por unidad de medida — NUMERIC(12,4) para precisión decimal
    costo: Decimal = Field(
        default=Decimal("0.0000"),
        ge=0,
        sa_column=Column(Numeric(precision=12, scale=4), nullable=False),
    )

    # D1: stock disponible del ingrediente — NUMERIC(10,3) para fracciones (0.5 kg, etc.)
    stock_cantidad: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(precision=10, scale=3), nullable=False, server_default="0"),
    )

    # RN-IN02: unidad de medida del ingrediente → FK al catálogo UnidadMedida
    unidad_medida_id: int = Field(foreign_key="unidades_medida.id", nullable=False, index=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)

    # Relación al catálogo (cargada selectin para poder exponer el código/símbolo en lecturas)
    unidad: Optional["UnidadMedida"] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    producto_ingredientes: List["ProductoIngrediente"] = Relationship(
        back_populates="ingrediente"
    )

    @property
    def activo(self) -> bool:
        return self.deleted_at is None

    @property
    def unidad_medida(self) -> Optional[str]:
        """Código de la unidad de medida (compat. de API: 'KG', 'L', ...)."""
        return self.unidad.codigo if self.unidad else None

    @property
    def unidad_simbolo(self) -> Optional[str]:
        return self.unidad.simbolo if self.unidad else None
