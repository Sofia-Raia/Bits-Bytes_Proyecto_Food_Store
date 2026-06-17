# app/modules/ingredientes/router.py
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.pagination import Paginated, paginar, offset_de
from app.modules.auth.dependencies import get_current_user, require_admin, require_role

from app.modules.ingredientes.schemas import (
    IngredienteCreate, IngredientePublic, IngredienteUpdate, IngredienteList,
    StockIngredienteUpdate, UnidadMedidaPublic,
)
from app.modules.ingredientes.service import IngredienteService

router = APIRouter()

_SORT_BY_VALUES = {'nombre', 'codigo', 'es_alergeno', 'created_at'}


def get_service(session: Session = Depends(get_session)) -> IngredienteService:
    return IngredienteService(session)


@router.get(
    "/unidades-medida",
    response_model=list[UnidadMedidaPublic],
    summary="Listar catálogo de unidades de medida [autenticado]",
)
def list_unidades_medida(
    svc: IngredienteService = Depends(get_service),
    _=Depends(get_current_user),
) -> list[UnidadMedidaPublic]:
    """
    Catálogo de unidades de medida (solo-lectura).
    El catálogo no tiene módulo propio: se expone desde su módulo dueño (ingredientes).
    """
    return svc.listar_unidades()


@router.post("/", response_model=IngredientePublic, status_code=status.HTTP_201_CREATED,
             summary="Crear ingrediente [ADMIN, STOCK]")
def create_ingrediente(
    data: IngredienteCreate,
    svc: IngredienteService = Depends(get_service),
    _=Depends(require_role(["ADMIN", "STOCK"])),
) -> IngredientePublic:
    return svc.create(data)


@router.get("/", response_model=Paginated[IngredientePublic], summary="Listar ingredientes")
def list_ingredientes(
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=10000)] = 100,
    incluir_inactivos: bool = False,
    nombre: Optional[str] = None,
    sort_by: str = 'nombre',
    sort_dir: str = 'asc',
    svc: IngredienteService = Depends(get_service),
    _=Depends(get_current_user),
) -> Paginated[IngredientePublic]:
    safe_sort_by  = sort_by  if sort_by  in _SORT_BY_VALUES else 'nombre'
    safe_sort_dir = sort_dir if sort_dir in ('asc', 'desc')  else 'asc'
    result: IngredienteList = svc.get_all(
        offset=offset_de(page, size), limit=size,
        incluir_inactivos=incluir_inactivos, nombre=nombre,
        sort_by=safe_sort_by, sort_dir=safe_sort_dir,
    )
    return paginar(result.data, result.total, page, size)


@router.get("/{ingrediente_id}", response_model=IngredientePublic)
def get_ingrediente(
    ingrediente_id: int,
    svc: IngredienteService = Depends(get_service),
    _=Depends(get_current_user),
) -> IngredientePublic:
    return svc.get_by_id(ingrediente_id)


@router.patch("/{ingrediente_id}", response_model=IngredientePublic,
              summary="Actualizar ingrediente [ADMIN, STOCK]")
def update_ingrediente(
    ingrediente_id: int,
    data: IngredienteUpdate,
    svc: IngredienteService = Depends(get_service),
    _=Depends(require_role(["ADMIN", "STOCK"])),
) -> IngredientePublic:
    return svc.update(ingrediente_id, data)


@router.delete("/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Desactivar ingrediente [ADMIN]")
def desactivar_ingrediente(
    ingrediente_id: int,
    svc: IngredienteService = Depends(get_service),
    _=Depends(require_admin),
) -> None:
    svc.desactivar(ingrediente_id)


@router.patch("/{ingrediente_id}/stock", response_model=IngredientePublic,
              summary="Reponer/ajustar stock de ingrediente [ADMIN, STOCK]")
def actualizar_stock_ingrediente(
    ingrediente_id: int,
    data: StockIngredienteUpdate,
    svc: IngredienteService = Depends(get_service),
    _=Depends(require_role(["ADMIN", "STOCK"])),
) -> IngredientePublic:
    """
    Setea el stock del ingrediente al valor absoluto indicado.
    Sirve tanto para reposición como para ajuste por merma.
    """
    return svc.actualizar_stock(ingrediente_id, data.stock_cantidad)


@router.patch("/{ingrediente_id}/reactivar", response_model=IngredientePublic,
              summary="Reactivar ingrediente [ADMIN]")
def reactivar_ingrediente(
    ingrediente_id: int,
    svc: IngredienteService = Depends(get_service),
    _=Depends(require_admin),
) -> IngredientePublic:
    return svc.reactivar(ingrediente_id)
