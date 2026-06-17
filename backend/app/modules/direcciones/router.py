# app/modules/direcciones/router.py
"""
Router del módulo direcciones.


Endpoints:
  GET    /                    CLIENT: propias; ADMIN: todas (?usuario_id=N opcional)
  POST   /                    Crea dirección para el usuario del JWT
  GET    /{id}                Ownership + ADMIN
  PATCH  /{id}                Ownership + ADMIN
  DELETE /{id}                Soft delete, ownership + ADMIN
  PATCH  /{id}/principal      Marca como principal + desmarca otras
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.pagination import Paginated, paginar, offset_de
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import Usuario
from app.modules.direcciones.schemas import (
    DireccionCreate,
    DireccionList,
    DireccionPublic,
    DireccionUpdate,
)
from app.modules.direcciones.service import DireccionService

router = APIRouter()


def get_service(session: Session = Depends(get_session)) -> DireccionService:
    return DireccionService(session)


@router.get("/", response_model=Paginated[DireccionPublic], summary="Listar direcciones [auth]")
def list_direcciones(
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    usuario_id: Optional[int] = None,   # solo honrado para ADMIN
    svc: DireccionService = Depends(get_service),
    current: tuple[Usuario, list[str]] = Depends(get_current_user),
) -> Paginated[DireccionPublic]:
    user, roles = current
    result: DireccionList = svc.get_all(
        usuario_id=user.id,
        roles=roles,
        offset=offset_de(page, size),
        limit=size,
        filtro_usuario_id=usuario_id if "ADMIN" in roles else None,
    )
    return paginar(result.data, result.total, page, size)


@router.post(
    "/",
    response_model=DireccionPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear dirección [auth]",
)
def create_direccion(
    data: DireccionCreate,
    svc: DireccionService = Depends(get_service),
    current: tuple[Usuario, list[str]] = Depends(get_current_user),
) -> DireccionPublic:
    user, _ = current
    return svc.create(data, user.id)


@router.get(
    "/{dir_id}",
    response_model=DireccionPublic,
    summary="Detalle dirección [auth, ownership]",
)
def get_direccion(
    dir_id: int,
    svc: DireccionService = Depends(get_service),
    current: tuple[Usuario, list[str]] = Depends(get_current_user),
) -> DireccionPublic:
    user, roles = current
    return svc.get_by_id(dir_id, user.id, roles)


@router.patch(
    "/{dir_id}",
    response_model=DireccionPublic,
    summary="Actualizar dirección [auth, ownership]",
)
def update_direccion(
    dir_id: int,
    data: DireccionUpdate,
    svc: DireccionService = Depends(get_service),
    current: tuple[Usuario, list[str]] = Depends(get_current_user),
) -> DireccionPublic:
    user, roles = current
    return svc.update(dir_id, data, user.id, roles)


@router.delete(
    "/{dir_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar dirección — soft delete [auth, ownership]",
)
def delete_direccion(
    dir_id: int,
    svc: DireccionService = Depends(get_service),
    current: tuple[Usuario, list[str]] = Depends(get_current_user),
) -> None:
    user, roles = current
    svc.soft_delete(dir_id, user.id, roles)


@router.patch(
    "/{dir_id}/principal",
    response_model=DireccionPublic,
    summary="Marcar como dirección principal [auth, ownership]",
)
def marcar_principal(
    dir_id: int,
    svc: DireccionService = Depends(get_service),
    current: tuple[Usuario, list[str]] = Depends(get_current_user),
) -> DireccionPublic:
    user, roles = current
    return svc.marcar_principal(dir_id, user.id, roles)
