# app/modules/direcciones/schemas.py
"""
Schemas del módulo direcciones.


"""
from datetime import datetime
from typing import List, Optional

from pydantic import Field
from sqlmodel import SQLModel


class DireccionCreate(SQLModel):
    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: str = Field(min_length=3, max_length=200)
    linea2: Optional[str] = Field(default=None, max_length=200)
    ciudad: str = Field(min_length=2, max_length=100)
    provincia: Optional[str] = Field(default=None, max_length=100)
    codigo_postal: Optional[str] = Field(default=None, max_length=10)
    es_principal: bool = False


class DireccionUpdate(SQLModel):
    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: Optional[str] = Field(default=None, min_length=3, max_length=200)
    linea2: Optional[str] = None
    ciudad: Optional[str] = Field(default=None, min_length=2, max_length=100)
    provincia: Optional[str] = None
    codigo_postal: Optional[str] = None
    es_principal: Optional[bool] = None


class DireccionPublic(SQLModel):
    id: int
    usuario_id: int
    alias: Optional[str] = None
    linea1: str
    linea2: Optional[str] = None
    ciudad: str
    provincia: Optional[str] = None
    codigo_postal: Optional[str] = None
    es_principal: bool
    created_at: datetime
    updated_at: datetime


class DireccionList(SQLModel):
    data: List[DireccionPublic]
    total: int
