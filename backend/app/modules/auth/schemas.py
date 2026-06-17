# app/modules/auth/schemas.py
from typing import List, Optional
from sqlmodel import SQLModel, Field


class LoginRequest(SQLModel):
    email:    str
    password: str


class LoginResponse(SQLModel):
    """
    Datos del usuario autenticado devueltos al cliente.
    Los tokens NO se incluyen aquí: viajan en cookies HttpOnly
    seteadas directamente en el Response HTTP.
    """
    id:       int
    email:    str
    nombre:   str
    apellido: str
    roles:    List[str]


class RegisterRequest(SQLModel):
    """
    Body para el registro público de nuevos usuarios (T-B04).
    El rol CLIENT se asigna automáticamente — el cliente no elige rol.
    """
    nombre:   str            = Field(min_length=2, max_length=80)
    apellido: str            = Field(min_length=2, max_length=80)
    email:    str
    password: str            = Field(min_length=8)
    celular:  Optional[str]  = Field(default=None, max_length=20)
