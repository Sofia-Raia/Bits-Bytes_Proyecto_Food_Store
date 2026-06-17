# app/modules/productos/schemas.py
"""
Schemas del módulo productos.

MoneyDecimal / QuantityDecimal — campos Decimal que se serializan como float en JSON.
precio_costo — calculado on-the-fly en el service, nunca persistido .
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from pydantic import model_validator
from sqlmodel import SQLModel, Field

from app.core.types import MoneyDecimal, QuantityDecimal
from app.modules.productos.models import TipoProducto


# ── Ingrediente dentro de un producto (input) ─────────────────────────────────

class ProductoIngredienteInput(SQLModel):
    """Input de un ingrediente al crear/actualizar un producto."""
    ingrediente_id: int
    cantidad: Decimal = Field(gt=0, description="Cantidad del ingrediente por unidad de producto")
    es_removible: bool = False
    es_opcional: bool = False


# ── Ingrediente dentro de un producto (output) ───────────────────────────────

class IngredienteEnProducto(SQLModel):
    """Vista enriquecida de un ingrediente en un producto (RN-PR05)."""
    id: int
    nombre: str
    es_alergeno: bool
    es_removible: bool
    es_opcional: bool
    cantidad: QuantityDecimal           # cantidad por unidad de producto
    unidad_medida: str                  # código de la unidad del ingrediente (KG, L, ...)
    costo_unitario: MoneyDecimal        # costo del ingrediente por su unidad
    subtotal_costo: MoneyDecimal        # cantidad × costo_unitario


# ── Categoría dentro de un producto (output) ─────────────────────────────────

class CategoriaEnProducto(SQLModel):
    id: int
    nombre: str
    es_principal: bool


# ── Producto CRUD ─────────────────────────────────────────────────────────────

class ProductoCreate(SQLModel):
    nombre: str = Field(min_length=2, max_length=200)
    descripcion: Optional[str] = None
    imagenes_url: List[str] = Field(default_factory=list)
    tiempo_prep_min: Optional[int] = Field(default=None, ge=0)
    tipo: TipoProducto
    precio_base: Decimal = Field(ge=0, default=Decimal("0.00"))
    stock_cantidad: int = Field(ge=0, default=0)
    disponible: bool = True
    # ERD: unidad de venta (FK al catálogo UnidadMedida). NULL = se vende por pieza.
    unidad_venta_id: Optional[int] = None
    categoria_ids: List[int] = Field(default_factory=list)
    ingredientes: List[ProductoIngredienteInput] = Field(default_factory=list)


class ProductoUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=200)
    descripcion: Optional[str] = None
    imagenes_url: Optional[List[str]] = None
    tiempo_prep_min: Optional[int] = Field(default=None, ge=0)
    tipo: Optional[TipoProducto] = None
    precio_base: Optional[Decimal] = Field(default=None, ge=0)
    stock_cantidad: Optional[int] = Field(default=None, ge=0)
    disponible: Optional[bool] = None
    unidad_venta_id: Optional[int] = None
    categoria_ids: Optional[List[int]] = None
    ingredientes: Optional[List[ProductoIngredienteInput]] = None


class ProductoPublic(SQLModel):
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    imagenes_url: List[str] = []
    tiempo_prep_min: Optional[int] = None
    tipo: TipoProducto
    precio_base: MoneyDecimal
    # RN-PR05: calculado on-the-fly, nunca persistido
    precio_costo: MoneyDecimal
    stock_cantidad: int
    disponible: bool
    unidad_venta_id: Optional[int] = None
    activo: bool
    categorias: List[CategoriaEnProducto] = []
    ingredientes: List[IngredienteEnProducto] = []
    created_at: datetime
    updated_at: datetime


class ProductoList(SQLModel):
    data: List[ProductoPublic]
    total: int


# ── Endpoints de conveniencia ────────────────────────────────────────────────

class DisponibilidadUpdate(SQLModel):
    disponible: bool


class StockUpdate(SQLModel):
    stock_cantidad: int = Field(ge=0)


# ── Aplicar margen masivo ─────────────────────────────────────────────────────

class AplicarMargenScope(str, Enum):
    PRODUCTOS = "productos"
    CATEGORIA = "categoria"


class AplicarMargenRequest(SQLModel):
    """
    Body para PATCH /api/v1/productos/aplicar-margen.
    Exactamente uno de {producto_ids, categoria_id} debe venir según el scope.
    """
    scope: AplicarMargenScope
    margen_porcentaje: Decimal = Field(
        ge=0, le=10000,
        description="Margen sobre precio_costo en porcentaje. Ej: 30 → +30 %.",
    )
    producto_ids: Optional[List[int]] = None   # requerido si scope="productos"
    categoria_id: Optional[int] = None         # requerido si scope="categoria"

    @model_validator(mode="after")
    def _validar_scope(self) -> "AplicarMargenRequest":
        if self.scope == AplicarMargenScope.PRODUCTOS and not self.producto_ids:
            raise ValueError("scope='productos' requiere producto_ids")
        if self.scope == AplicarMargenScope.CATEGORIA and self.categoria_id is None:
            raise ValueError("scope='categoria' requiere categoria_id")
        return self


class ProductoMargenResult(SQLModel):
    producto_id: int
    nombre: str
    precio_anterior: MoneyDecimal
    precio_costo: MoneyDecimal
    precio_nuevo: MoneyDecimal


class ProductoIgnorado(SQLModel):
    producto_id: int
    razon: str


class AplicarMargenResponse(SQLModel):
    actualizados: List[ProductoMargenResult]
    ignorados: List[ProductoIgnorado]
