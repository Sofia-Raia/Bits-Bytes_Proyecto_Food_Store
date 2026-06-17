# app/modules/usuarios/service.py
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session

from app.core.exceptions.custom_exceptions import (
    ConflictError,
    DuplicateResourceError,
    ResourceNotFoundError,
    ValidationError,
)
from app.modules.auth.security import hash_password
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import (
    UsuarioPublic, UsuarioCreate, UsuarioUpdate,
    UsuarioListItem, UsuarioListPaginated,
)
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork


def _to_public(usuario: Usuario, roles: list[str]) -> UsuarioPublic:
    return UsuarioPublic(
        id=usuario.id, email=usuario.email,
        nombre=usuario.nombre, apellido=usuario.apellido,
        celular=usuario.celular, roles=roles, activo=usuario.activo,
    )


def _to_list_item(usuario: Usuario, roles: list[str]) -> UsuarioListItem:
    return UsuarioListItem(
        id=usuario.id, email=usuario.email,
        nombre=usuario.nombre, apellido=usuario.apellido,
        celular=usuario.celular, roles=roles, activo=usuario.activo,
        created_at=usuario.created_at,
    )


class UsuarioService:

    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: UsuarioUnitOfWork, id: int) -> Usuario:
        usuario = uow.usuarios.get_by_id(id)
        if not usuario:
            raise ResourceNotFoundError(f"Usuario con id={id} no encontrado")
        return usuario

    # ── Consultas ──────────────────────────────────────────────────────────────

    def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        incluir_inactivos: bool = False,
        nombre: Optional[str] = None,
        sort_by: str = 'nombre',
        sort_dir: str = 'asc',
    ) -> UsuarioListPaginated:
        with UsuarioUnitOfWork(self._session) as uow:
            total    = uow.usuarios.count(incluir_inactivos, nombre)
            usuarios = uow.usuarios.get_all_paginado(
                offset, limit, incluir_inactivos, nombre,
                sort_by=sort_by, sort_dir=sort_dir,
            )
            data     = [
                _to_list_item(u, uow.usuarios.get_roles(u.id)) for u in usuarios
            ]
            result = UsuarioListPaginated(total=total, data=data)
        return result

    def get_by_id(self, id: int) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._get_or_404(uow, id)
            result  = _to_public(usuario, uow.usuarios.get_roles(usuario.id))
        return result

    # ── Mutaciones ─────────────────────────────────────────────────────────────

    def crear(self, data: UsuarioCreate, admin_id: int) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            if uow.usuarios.get_by_email(data.email):
                raise DuplicateResourceError("El email ya está registrado")
            for codigo in data.roles:
                if not uow.usuarios.rol_existe(codigo):
                    raise ValidationError(f"Rol inválido: {codigo}")

            usuario = Usuario(
                nombre=data.nombre, apellido=data.apellido, email=data.email,
                celular=data.celular, password_hash=hash_password(data.password),
            )
            uow.usuarios.add(usuario)
            uow.usuarios.set_roles(usuario.id, data.roles, admin_id)
            result = _to_public(usuario, data.roles)
        return result

    def editar(self, id: int, data: UsuarioUpdate, admin_id: int) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._get_or_404(uow, id)
            if not usuario.activo:
                raise ConflictError("No se puede editar un usuario inactivo")

            if data.email is not None:
                existing = uow.usuarios.get_by_email(data.email)
                if existing and existing.id != id:
                    raise DuplicateResourceError("El email ya está registrado")
                usuario.email = data.email

            if data.nombre   is not None: usuario.nombre   = data.nombre
            if data.apellido is not None: usuario.apellido = data.apellido
            if data.celular  is not None: usuario.celular  = data.celular
            if data.password is not None: usuario.password_hash = hash_password(data.password)

            usuario.updated_at = datetime.now(timezone.utc)
            uow.usuarios.add(usuario)

            if data.roles is not None:
                for codigo in data.roles:
                    if not uow.usuarios.rol_existe(codigo):
                        raise ValidationError(f"Rol inválido: {codigo}")

                # RN-RB04: no quitarle el rol ADMIN al último ADMIN activo
                roles_actuales = uow.usuarios.get_roles(id)
                quitando_admin = "ADMIN" in roles_actuales and "ADMIN" not in data.roles
                if quitando_admin and uow.usuarios.count_admins_activos() <= 1:
                    raise ConflictError(
                        "No se puede quitar el rol ADMIN: es el último administrador activo del sistema"
                    )

                uow.usuarios.set_roles(id, data.roles, admin_id)
                roles_result = data.roles
            else:
                roles_result = uow.usuarios.get_roles(id)

            result = _to_public(usuario, roles_result)
        return result

    def desactivar(self, id: int, admin_id: int) -> None:
        if admin_id == id:
            raise ConflictError("No podés desactivar tu propio usuario")
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._get_or_404(uow, id)
            if not usuario.activo:
                raise ConflictError("El usuario ya está inactivo")

            # RN-RB04: no desactivar al último ADMIN activo
            roles_actuales = uow.usuarios.get_roles(id)
            if "ADMIN" in roles_actuales and uow.usuarios.count_admins_activos() <= 1:
                raise ConflictError(
                    "No se puede desactivar al último administrador activo del sistema"
                )

            usuario.deleted_at = datetime.now(timezone.utc)
            usuario.updated_at = datetime.now(timezone.utc)
            uow.usuarios.add(usuario)

    def reactivar(self, id: int) -> UsuarioPublic:
        with UsuarioUnitOfWork(self._session) as uow:
            usuario = self._get_or_404(uow, id)
            if usuario.activo:
                raise ConflictError("El usuario ya está activo")
            usuario.deleted_at = None
            usuario.updated_at = datetime.now(timezone.utc)
            uow.usuarios.add(usuario)
            result = _to_public(usuario, uow.usuarios.get_roles(id))
        return result
