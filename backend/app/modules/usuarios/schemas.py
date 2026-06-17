# app/modules/usuarios/schemas.py
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel


class UsuarioPublic(SQLModel):
    id:       int
    email:    str
    nombre:   str
    apellido: str
    celular:  Optional[str]
    roles:    List[str]
    activo:   bool


class UsuarioCreate(SQLModel):
    nombre:   str
    apellido: str
    email:    str
    celular:  Optional[str] = None
    password: str
    roles:    List[str] = []


class UsuarioUpdate(SQLModel):
    nombre:   Optional[str] = None
    apellido: Optional[str] = None
    email:    Optional[str] = None
    celular:  Optional[str] = None
    password: Optional[str] = None
    roles:    Optional[List[str]] = None


class UsuarioListItem(SQLModel):
    id:         int
    email:      str
    nombre:     str
    apellido:   str
    celular:    Optional[str]
    roles:      List[str]
    activo:     bool
    created_at: datetime


class UsuarioListPaginated(SQLModel):
    total: int
    data:  List[UsuarioListItem]
