# app/modules/ingredientes/schemas.py
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlmodel import SQLModel, Field

from app.core.types import MoneyDecimal, QuantityDecimal


# ── Catálogo UnidadMedida (solo-lectura) ──────────────────────────────────────

class UnidadMedidaPublic(SQLModel):
    """Vista pública de una unidad de medida del catálogo."""
    id: int
    codigo: str
    nombre: str
    simbolo: str
    tipo: str


# ── Ingrediente CRUD ──────────────────────────────────────────────────────────

class IngredienteCreate(SQLModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: Optional[str] = None
    es_alergeno: bool = False
    # RN-IN01: costo por unidad — Pydantic acepta float del JSON y lo coerce a Decimal
    costo: Decimal = Field(ge=0, description="Costo por unidad de medida. Debe ser ≥ 0.")
    # RN-IN02: código de la unidad de medida (FK al catálogo, resuelto en el service)
    unidad_medida: str = Field(description="Código de la unidad de medida (ej: KG, L, UNIDADES).")
    # D1: stock inicial — Numeric(10,3), default 0
    stock_cantidad: Decimal = Field(ge=0, default=Decimal("0"))


class IngredienteUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=100)
    descripcion: Optional[str] = None
    es_alergeno: Optional[bool] = None
    costo: Optional[Decimal] = Field(default=None, ge=0)
    unidad_medida: Optional[str] = None
    stock_cantidad: Optional[Decimal] = Field(default=None, ge=0)


class IngredientePublic(SQLModel):
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    es_alergeno: bool
    # MoneyDecimal: serializado como float en JSON (no como string)
    costo: MoneyDecimal
    # Código de la unidad (compat. de API) + id de la FK + símbolo para UI
    unidad_medida: str
    unidad_medida_id: int
    unidad_simbolo: Optional[str] = None
    # D1: stock — QuantityDecimal serializa como float en JSON
    stock_cantidad: QuantityDecimal
    activo: bool
    created_at: datetime
    updated_at: datetime


class IngredienteList(SQLModel):
    data: List[IngredientePublic]
    total: int


# ── Schema para endpoint PATCH /ingredientes/{id}/stock ───────────────────────

class StockIngredienteUpdate(SQLModel):
    """Body para reponer/ajustar stock de un ingrediente (D4: acepta cualquier valor >= 0)."""
    stock_cantidad: Decimal = Field(ge=0)
