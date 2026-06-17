# app/modules/usuarios/models.py
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class Rol(SQLModel, table=True):
    __tablename__ = "roles"

    codigo:      str           = Field(primary_key=True, max_length=20)
    nombre:      str           = Field(max_length=50, unique=True)
    descripcion: Optional[str] = Field(default=None)

    usuario_roles: List["UsuarioRol"] = Relationship(back_populates="rol")


class Usuario(SQLModel, table=True):
    """
    Soft delete: activo = (deleted_at is None).
    Los roles se consultan directamente vía UsuarioRepository.get_roles()
    — no hay Relationship aquí para evitar la ambigüedad de FKs múltiples
    en la tabla usuario_roles.
    """
    __tablename__ = "usuarios"

    id:            Optional[int]      = Field(default=None, primary_key=True)
    nombre:        str                = Field(max_length=80)
    apellido:      str                = Field(max_length=80)
    email:         str                = Field(max_length=254, unique=True, index=True)
    celular:       Optional[str]      = Field(default=None, max_length=20)
    password_hash: str                = Field(max_length=200)
    created_at:    datetime           = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:    datetime           = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at:    Optional[datetime] = Field(default=None)

    @property
    def activo(self) -> bool:
        return self.deleted_at is None


class UsuarioRol(SQLModel, table=True):
    """
    Unión M2M Usuario ↔ Rol.
    Tiene dos FKs a usuarios (usuario_id y asignado_por_id), por eso
    NO se define Relationship inverso hacia Usuario — se evita la
    AmbiguousForeignKeysError de SQLAlchemy.
    """
    __tablename__ = "usuario_roles"

    usuario_id:      int           = Field(foreign_key="usuarios.id",  primary_key=True)
    rol_codigo:      str           = Field(foreign_key="roles.codigo", primary_key=True, max_length=20)
    asignado_por_id: Optional[int] = Field(default=None, foreign_key="usuarios.id")
    expires_at:      Optional[datetime] = Field(default=None)
    created_at:      datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    rol: Optional["Rol"] = Relationship(back_populates="usuario_roles")


class RefreshToken(SQLModel, table=True):
    """
    Refresh token emitido al iniciar sesión.

    Cada refresh token tiene un identificador único (jti) que viaja dentro del JWT.
    Permite revocar la sesión en el servidor: el logout marca revoked_at y el endpoint
    de refresh rechaza cualquier token cuyo jti esté revocado o no exista.
    """
    __tablename__ = "refresh_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuarios.id", nullable=False, index=True)
    jti: str = Field(max_length=64, unique=True, index=True)
    expires_at: datetime = Field(nullable=False)
    revoked_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
