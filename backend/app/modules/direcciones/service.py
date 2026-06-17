# app/modules/direcciones/service.py
"""
Service del módulo direcciones.


- Ownership: CLIENT solo accede a sus propias direcciones (filtrado por usuario_id).
  ADMIN puede ver y operar todas.
- es_principal auto-asignado: si es la primera dirección o se pasa es_principal=True,
  se desmarca todas las otras del usuario en el mismo UoW 
- Soft delete: solo setea deleted_at.
"""
from datetime import datetime, timezone

from sqlmodel import Session

from app.core.exceptions.custom_exceptions import ResourceNotFoundError
from app.modules.direcciones.models import DireccionEntrega
from app.modules.direcciones.schemas import (
    DireccionCreate,
    DireccionList,
    DireccionPublic,
    DireccionUpdate,
)
from app.modules.direcciones.unit_of_work import DireccionUnitOfWork


def _to_public(d: DireccionEntrega) -> DireccionPublic:
    return DireccionPublic(
        id=d.id,
        usuario_id=d.usuario_id,
        alias=d.alias,
        linea1=d.linea1,
        linea2=d.linea2,
        ciudad=d.ciudad,
        provincia=d.provincia,
        codigo_postal=d.codigo_postal,
        es_principal=d.es_principal,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


def _is_admin(roles: list[str]) -> bool:
    return "ADMIN" in roles


class DireccionService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_or_404(
        self,
        uow: DireccionUnitOfWork,
        dir_id: int,
        usuario_id: int,
        roles: list[str],
    ) -> DireccionEntrega:
        """
        Carga la dirección aplicando ownership según el rol.
        ADMIN puede ver cualquier dirección activa; CLIENT solo las propias.
        """
        if _is_admin(roles):
            d = uow.direcciones.get_by_id_activa(dir_id)
        else:
            d = uow.direcciones.get_by_id_y_usuario(dir_id, usuario_id)

        if not d:
            raise ResourceNotFoundError(f"Dirección con id={dir_id} no encontrada.")
        return d

    # ── Casos de uso ──────────────────────────────────────────────────────────

    def get_all(
        self,
        usuario_id: int,
        roles: list[str],
        offset: int = 0,
        limit: int = 20,
        filtro_usuario_id: int | None = None,
    ) -> DireccionList:
        """
        Lista direcciones.
        - ADMIN: todas (con filtro opcional ?usuario_id).
        - CLIENT: solo las propias.
        """
        with DireccionUnitOfWork(self._session) as uow:
            # ADMIN ve "todas" SOLO si pide explícitamente un usuario (?usuario_id).
            # Sin ese filtro, la página es personal: cada quien ve solo las suyas.
            if _is_admin(roles) and filtro_usuario_id is not None:
                dirs = uow.direcciones.get_all_admin(
                    offset=offset, limit=limit, usuario_id=filtro_usuario_id
                )
                total = uow.direcciones.count_admin(usuario_id=filtro_usuario_id)
            else:
                dirs = uow.direcciones.get_all_by_usuario(
                    usuario_id, offset=offset, limit=limit
                )
                total = uow.direcciones.count_by_usuario(usuario_id)

            return DireccionList(
                data=[_to_public(d) for d in dirs],
                total=total,
            )

    def create(self, data: DireccionCreate, usuario_id: int) -> DireccionPublic:
        """
        Crea una nueva dirección para el usuario del JWT.

        Lógica principal (RN-DI01, RN-DI02):
        - Si es la primera dirección del usuario → fuerza es_principal=True.
        - Si data.es_principal=True → desmarcar las otras del mismo usuario.
        Ambas operaciones ocurren en el mismo UoW (atómica).
        """
        with DireccionUnitOfWork(self._session) as uow:
            total_existentes = uow.direcciones.count_activas_usuario(usuario_id)
            # Primera dirección o solicita ser principal → marcar como principal
            debe_ser_principal = data.es_principal or (total_existentes == 0)

            if debe_ser_principal:
                uow.direcciones.desmarcar_principal(usuario_id)

            nueva = DireccionEntrega(
                usuario_id=usuario_id,
                alias=data.alias,
                linea1=data.linea1,
                linea2=data.linea2,
                ciudad=data.ciudad,
                provincia=data.provincia,
                codigo_postal=data.codigo_postal,
                es_principal=debe_ser_principal,
            )
            uow.direcciones.add(nueva)
            result = _to_public(nueva)
        return result

    def get_by_id(
        self, dir_id: int, usuario_id: int, roles: list[str]
    ) -> DireccionPublic:
        with DireccionUnitOfWork(self._session) as uow:
            d = self._get_or_404(uow, dir_id, usuario_id, roles)
            return _to_public(d)

    def update(
        self,
        dir_id: int,
        data: DireccionUpdate,
        usuario_id: int,
        roles: list[str],
    ) -> DireccionPublic:
        """
        Actualiza una dirección.
        Si se setea es_principal=True, desmarca las otras del mismo usuario.
        """
        with DireccionUnitOfWork(self._session) as uow:
            d = self._get_or_404(uow, dir_id, usuario_id, roles)

            patch = data.model_dump(exclude_unset=True)

            # Si el patch quiere marcar como principal, desmarcar las otras primero
            if patch.get("es_principal") is True:
                uow.direcciones.desmarcar_principal(d.usuario_id)

            for field, value in patch.items():
                setattr(d, field, value)
            d.updated_at = datetime.now(timezone.utc)
            uow.direcciones.add(d)
            result = _to_public(d)
        return result

    def soft_delete(
        self, dir_id: int, usuario_id: int, roles: list[str]
    ) -> None:
        """Soft delete de una dirección (ownership + ADMIN)."""
        with DireccionUnitOfWork(self._session) as uow:
            d = self._get_or_404(uow, dir_id, usuario_id, roles)
            d.deleted_at = datetime.now(timezone.utc)
            d.updated_at = datetime.now(timezone.utc)
            uow.direcciones.add(d)

    def marcar_principal(
        self, dir_id: int, usuario_id: int, roles: list[str]
    ) -> DireccionPublic:
        """
        Marca una dirección como principal y desmarca todas las otras del mismo
        usuario. Operación atómica en un solo UoW.
        """
        with DireccionUnitOfWork(self._session) as uow:
            d = self._get_or_404(uow, dir_id, usuario_id, roles)

            # Desmarcar todas (incluyendo la actual si ya era principal)
            uow.direcciones.desmarcar_principal(d.usuario_id)

            d.es_principal = True
            d.updated_at = datetime.now(timezone.utc)
            uow.direcciones.add(d)
            result = _to_public(d)
        return result
