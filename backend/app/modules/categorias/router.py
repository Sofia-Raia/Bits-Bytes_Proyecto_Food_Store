# app/modules/categorias/router.py
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.pagination import Paginated, paginar, offset_de
from app.modules.auth.dependencies import get_current_user, require_admin, require_role

from app.modules.categorias.schemas import (
    CategoriaCreate, CategoriaPublic, CategoriaUpdate,
    CategoriaList, CategoriaTreeList,
)
from app.modules.categorias.service import CategoriaService

router = APIRouter()


def get_service(session: Session = Depends(get_session)) -> CategoriaService:
    return CategoriaService(session)


@router.get("/tree", response_model=CategoriaTreeList, summary="Árbol de categorías")
def get_tree(
    incluir_inactivos: bool = False,
    svc: CategoriaService = Depends(get_service),
    _ = Depends(get_current_user),
) -> CategoriaTreeList:
    return svc.get_tree(incluir_inactivos=incluir_inactivos)


@router.get("/{categoria_id}/subcategorias", response_model=Paginated[CategoriaPublic])
def get_subcategorias(
    categoria_id: int,
    svc: CategoriaService = Depends(get_service),
    _ = Depends(get_current_user),
) -> Paginated[CategoriaPublic]:
    result: CategoriaList = svc.get_subcategorias(categoria_id)
    # Sub-colección no paginada: se devuelve como una única página completa.
    return paginar(result.data, result.total, page=1, size=max(result.total, 1))


@router.post("/", response_model=CategoriaPublic, status_code=status.HTTP_201_CREATED,
             summary="Crear categoría [ADMIN, STOCK]")
def create_categoria(
    data: CategoriaCreate,
    svc: CategoriaService = Depends(get_service),
    _ = Depends(require_role(["ADMIN", "STOCK"])),
) -> CategoriaPublic:
    return svc.create(data)


# BACKEND-2: GET /categorias público (sin autenticación requerida)
@router.get("/", response_model=Paginated[CategoriaPublic], summary="Listar categorías [público]")
def list_categorias(
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 100,
    incluir_inactivos: bool = False,
    nombre: Optional[str] = None,
    svc: CategoriaService = Depends(get_service),
) -> Paginated[CategoriaPublic]:
    result: CategoriaList = svc.get_all(
        offset=offset_de(page, size), limit=size,
        incluir_inactivos=incluir_inactivos, nombre=nombre,
    )
    return paginar(result.data, result.total, page, size)


# BACKEND-2: GET /categorias/{id} público (sin autenticación requerida)
@router.get("/{categoria_id}", response_model=CategoriaPublic, summary="Detalle categoría [público]")
def get_categoria(
    categoria_id: int,
    svc: CategoriaService = Depends(get_service),
) -> CategoriaPublic:
    return svc.get_by_id(categoria_id)


@router.patch("/{categoria_id}", response_model=CategoriaPublic,
              summary="Actualizar categoría [ADMIN, STOCK]")
def update_categoria(
    categoria_id: int,
    data: CategoriaUpdate,
    svc: CategoriaService = Depends(get_service),
    _ = Depends(require_role(["ADMIN", "STOCK"])),
) -> CategoriaPublic:
    return svc.update(categoria_id, data)


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Desactivar categoría — borrado lógico [ADMIN]")
def desactivar_categoria(
    categoria_id: int,
    svc: CategoriaService = Depends(get_service),
    _ = Depends(require_admin),
) -> None:
    svc.desactivar(categoria_id)


@router.patch("/{categoria_id}/reactivar", response_model=CategoriaPublic,
              summary="Reactivar categoría [ADMIN]")
def reactivar_categoria(
    categoria_id: int,
    svc: CategoriaService = Depends(get_service),
    _ = Depends(require_admin),
) -> CategoriaPublic:
    return svc.reactivar(categoria_id)
