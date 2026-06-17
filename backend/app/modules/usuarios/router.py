# app/modules/usuarios/router.py
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.database import get_session
from app.core.pagination import Paginated, paginar, offset_de
from app.modules.auth.dependencies import get_current_user, require_admin
from app.modules.usuarios.schemas import (
    UsuarioPublic, UsuarioCreate, UsuarioUpdate, UsuarioListPaginated, UsuarioListItem,
)
from app.modules.usuarios.service import UsuarioService

router = APIRouter()

_SORT_BY_VALUES = {'nombre', 'apellido', 'email', 'created_at'}


def get_service(session: Session = Depends(get_session)) -> UsuarioService:
    return UsuarioService(session)


@router.get("/", response_model=Paginated[UsuarioListItem])
def listar_usuarios(
    page: Annotated[int, Query(ge=1)] = 1,
    size:  Annotated[int, Query(ge=1, le=100)] = 20,
    incluir_inactivos: bool = False,
    nombre: Optional[str] = None,
    sort_by:  str = 'nombre',
    sort_dir: str = 'asc',
    svc: UsuarioService = Depends(get_service),
    _=Depends(require_admin),
) -> Paginated[UsuarioListItem]:
    safe_sort_by  = sort_by  if sort_by  in _SORT_BY_VALUES else 'nombre'
    safe_sort_dir = sort_dir if sort_dir in ('asc', 'desc')  else 'asc'
    result: UsuarioListPaginated = svc.get_all(
        offset_de(page, size), size, incluir_inactivos, nombre, safe_sort_by, safe_sort_dir,
    )
    return paginar(result.data, result.total, page, size)


@router.post("/", response_model=UsuarioPublic, status_code=201)
def crear_usuario(
    data: UsuarioCreate,
    svc: UsuarioService = Depends(get_service),
    current=Depends(require_admin),
):
    admin, _ = current
    return svc.crear(data, admin.id)


@router.get("/{id}", response_model=UsuarioPublic)
def obtener_usuario(
    id: int,
    svc: UsuarioService = Depends(get_service),
    _=Depends(require_admin),
):
    return svc.get_by_id(id)


@router.patch("/{id}", response_model=UsuarioPublic)
def editar_usuario(
    id: int,
    data: UsuarioUpdate,
    svc: UsuarioService = Depends(get_service),
    current=Depends(require_admin),
):
    admin, _ = current
    return svc.editar(id, data, admin.id)


@router.delete("/{id}", status_code=204)
def desactivar_usuario(
    id: int,
    svc: UsuarioService = Depends(get_service),
    current=Depends(require_admin),
):
    admin, _ = current
    svc.desactivar(id, admin.id)


@router.patch("/{id}/reactivar", response_model=UsuarioPublic)
def reactivar_usuario(
    id: int,
    svc: UsuarioService = Depends(get_service),
    _=Depends(require_admin),
):
    return svc.reactivar(id)
