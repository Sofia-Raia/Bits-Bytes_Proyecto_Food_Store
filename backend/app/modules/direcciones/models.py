# app/modules/direcciones/models.py
"""
Modelo de dominio para direcciones de entrega.

Sprint 6 — T-B30:
- DireccionEntrega: dirección postal de un usuario.
  * Soft delete via deleted_at (activo como @property).
  * Solo una dirección por usuario puede tener es_principal=True.
  * lat/lon se omiten en Versión B (deuda técnica).
"""
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class DireccionEntrega(SQLModel, table=True):
    """
    Dirección de entrega de un usuario.

    Versión B simplificación: sin latitud/longitud (Decimal no enseñado).
    Soft delete: solo deleted_at. `activo` como @property.
    """

    __tablename__ = "direcciones_entrega"

    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(nullable=False, foreign_key="usuarios.id", index=True)

    alias: Optional[str] = Field(default=None, max_length=50)   # "Casa", "Trabajo"
    linea1: str = Field(nullable=False, max_length=200)
    linea2: Optional[str] = Field(default=None, max_length=200)
    ciudad: str = Field(nullable=False, max_length=100)
    provincia: Optional[str] = Field(default=None, max_length=100)
    codigo_postal: Optional[str] = Field(default=None, max_length=10)

    es_principal: bool = Field(default=False, nullable=False)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = Field(default=None)

    @property
    def activo(self) -> bool:
        """True si la dirección no fue eliminada (soft delete)."""
        return self.deleted_at is None
