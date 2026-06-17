# app/modules/categorias/schemas.py
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field


class CategoriaCreate(SQLModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    parent_id: Optional[int] = None


class CategoriaUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=100)
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    parent_id: Optional[int] = None


class CategoriaPublic(SQLModel):
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    parent_id: Optional[int] = None
    activo: bool
    created_at: datetime
    updated_at: datetime


class CategoriaList(SQLModel):
    data: List[CategoriaPublic]
    total: int


class CategoriaTree(SQLModel):
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    parent_id: Optional[int] = None
    activo: bool
    created_at: datetime
    updated_at: datetime
    subcategorias: List["CategoriaTree"] = []


CategoriaTree.model_rebuild()


class CategoriaTreeList(SQLModel):
    data: List[CategoriaTree]
    total: int
