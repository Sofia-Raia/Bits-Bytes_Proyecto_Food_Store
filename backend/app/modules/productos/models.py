# app/modules/productos/models.py
"""
Modelos del módulo productos.

Tablas:
  - productos           — catálogo de productos (TERMINADO | MANUFACTURADO)
  - producto_categorias — M2M productos ↔ categorías (con bandera es_principal)
  - producto_ingredientes — M2M productos ↔ ingredientes (con cantidad y es_removible)

Notas de diseño:
  - precio_base: NUMERIC(12,2) — sin errores de punto flotante.
  - cantidad (ProductoIngrediente): NUMERIC(12,4) — permite fracciones como 0.250 kg.
  - precio_costo NO se persiste: se calcula on-the-fly en el service.
  - Borrado lógico via deleted_at; activo es @property derivada.
"""
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import ARRAY, Column, Enum as SAEnum, Numeric, Text
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.modules.ingredientes.models import Ingrediente
    from app.modules.categorias.models import Categoria



class TipoProducto(str, Enum):
    """
    TERMINADO:      producto adquirido/revendido tal cual. Sin lista de ingredientes
                    obligatoria; precio_costo = 0.
    MANUFACTURADO:  producto elaborado internamente. Requiere al menos un ingrediente
                    con cantidad > 0; precio_costo se calcula on-the-fly.
    """
    TERMINADO     = "TERMINADO"
    MANUFACTURADO = "MANUFACTURADO"


class Producto(SQLModel, table=True):
    """
    Producto del catálogo.

    precio_base: precio de venta al público — NUMERIC.
    stock_cantidad: unidades físicas disponibles. Disminuye al CONFIRMAR pedido;
                    se restaura al CANCELAR si ya estaba decrementado.
    tipo: TipoProducto — determina si se calcula precio_costo.
    """
    __tablename__ = "productos"

    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(max_length=20, unique=True, index=True)
    nombre: str = Field(min_length=2, max_length=200, unique=True, index=True)
    descripcion: Optional[str] = Field(default=None)

    # Galería de imágenes — TEXT[] (array de URLs). Primer elemento = imagen principal.
    imagenes_url: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False, server_default="{}"),
    )

    # Tiempo estimado de preparación en minutos (opcional)
    tiempo_prep_min: Optional[int] = Field(default=None, ge=0)

    tipo: TipoProducto = Field(
        sa_column=Column(SAEnum(TipoProducto), nullable=False)
    )

    # Precio de venta — NUMERIC(12,2)
    precio_base: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        sa_column=Column(Numeric(precision=12, scale=2), nullable=False),
    )

    stock_cantidad: int = Field(default=0, ge=0)
    disponible: bool = Field(default=True)

    # ERD: unidad de venta (resuelve ambigüedad de precio_base, ej: "$12.50 / kg"). NULL = por pieza.
    unidad_venta_id: Optional[int] = Field(
        default=None, foreign_key="unidades_medida.id", nullable=True
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)

    @property
    def activo(self) -> bool:
        return self.deleted_at is None

    categorias: List["ProductoCategoria"] = Relationship(back_populates="producto")
    ingredientes_link: List["ProductoIngrediente"] = Relationship(back_populates="producto")


class ProductoCategoria(SQLModel, table=True):
    """M2M Producto ↔ Categoría. es_principal marca la categoría de navegación primaria."""
    __tablename__ = "producto_categorias"

    producto_id: int = Field(
        foreign_key="productos.id", primary_key=True, ondelete="CASCADE"
    )
    categoria_id: int = Field(
        foreign_key="categorias.id", primary_key=True, ondelete="RESTRICT"
    )
    es_principal: bool = Field(default=False)

    producto: Optional["Producto"] = Relationship(back_populates="categorias")
     
    categoria: Optional["Categoria"] = Relationship(back_populates="producto_categorias")




class ProductoIngrediente(SQLModel, table=True):
    """
    M2M Producto ↔ Ingrediente.

    cantidad: NUMERIC(12,4) — cantidad del ingrediente necesaria para elaborar
              una unidad del producto, expresada en la unidad_medida del ingrediente.
              Ej: 0.250 (kg de harina) para una pizza.
    es_removible: el cliente puede pedir que se excluya este ingrediente.
    """
    __tablename__ = "producto_ingredientes"

    producto_id: int = Field(
        foreign_key="productos.id", primary_key=True, ondelete="CASCADE"
    )
    ingrediente_id: int = Field(
        foreign_key="ingredientes.id", primary_key=True, ondelete="RESTRICT"
    )
    # RN-PI01: cantidad necesaria — NUMERIC(12,4) para fracciones de kg/L
    cantidad: Decimal = Field(
        gt=0,
        sa_column=Column(Numeric(precision=12, scale=4), nullable=False),
    )
    # ERD: unidad de medida de la cantidad de la receta → FK al catálogo (NN).
    # Se asigna = unidad del ingrediente al armar la receta.
    unidad_medida_id: int = Field(foreign_key="unidades_medida.id", nullable=False)
    es_removible: bool = Field(default=False)
    # es_opcional: el cliente puede pedir este ingrediente como "extra" adicional
    es_opcional: bool = Field(default=False)

    producto: Optional["Producto"] = Relationship(back_populates="ingredientes_link")
    ingrediente: Optional["Ingrediente"] = Relationship(back_populates="producto_ingredientes")
