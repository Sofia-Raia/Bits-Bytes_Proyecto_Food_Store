# app/modules/productos/router.py
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.pagination import Paginated, paginar, offset_de
from app.modules.auth.dependencies import (
    get_current_user, get_current_user_optional, require_role,
)

from app.modules.productos.schemas import (
    AplicarMargenRequest, AplicarMargenResponse,
    DisponibilidadUpdate, StockUpdate,
    ProductoCreate, ProductoPublic, ProductoUpdate, ProductoList,
)
from app.modules.productos.service import ProductoService

router = APIRouter()

_SORT_BY_VALUES = {"nombre", "codigo", "precio_base", "stock_cantidad", "created_at"}


def get_service(session: Session = Depends(get_session)) -> ProductoService:
    return ProductoService(session)


# ── PATCH /aplicar-margen debe ir ANTES de /{producto_id} para que FastAPI
#    no lo interprete como un id. ────────────────────────────────────────────

@router.patch(
    "/aplicar-margen",
    response_model=AplicarMargenResponse,
    summary="Aplicar margen masivo a productos MANUFACTURADOS [ADMIN, STOCK]",
)
def aplicar_margen(
    data: AplicarMargenRequest,
    svc: ProductoService = Depends(get_service),
    _=Depends(require_role(["ADMIN", "STOCK"])),
) -> AplicarMargenResponse:
    return svc.aplicar_margen(data)


@router.post(
    "/",
    response_model=ProductoPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear producto [ADMIN, STOCK]",
)
def create_producto(
    data: ProductoCreate,
    svc: ProductoService = Depends(get_service),
    _=Depends(require_role(["ADMIN", "STOCK"])),
) -> ProductoPublic:
    return svc.create(data)


# BACKEND-2: GET /productos público.
# El catálogo es público y por defecto solo devuelve productos activos.
# incluir_inactivos solo se respeta si el solicitante está autenticado como
# ADMIN o STOCK (gestión); para anónimos o CLIENT se fuerza a False.
@router.get("/", response_model=Paginated[ProductoPublic], summary="Listar productos [público]")
def list_productos(
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=10000)] = 100,
    incluir_inactivos: bool = False,
    nombre: Optional[str] = None,
    categoria_id: Annotated[Optional[int], Query(ge=1)] = None,
    sort_by: str = "nombre",
    sort_dir: str = "asc",
    svc: ProductoService = Depends(get_service),
    current=Depends(get_current_user_optional),
) -> Paginated[ProductoPublic]:
    safe_sort_by = sort_by if sort_by in _SORT_BY_VALUES else "nombre"
    safe_sort_dir = sort_dir if sort_dir in ("asc", "desc") else "asc"

    roles = current[1] if current else []
    puede_gestionar = any(r in ("ADMIN", "STOCK") for r in roles)
    incluir = incluir_inactivos and puede_gestionar

    result: ProductoList = svc.get_all(
        offset=offset_de(page, size), limit=size,
        incluir_inactivos=incluir,
        nombre=nombre,
        categoria_id=categoria_id,
        sort_by=safe_sort_by, sort_dir=safe_sort_dir,
    )
    return paginar(result.data, result.total, page, size)


# BACKEND-2: GET /productos/{id} público.
@router.get("/{producto_id}", response_model=ProductoPublic, summary="Detalle producto [público]")
def get_producto(
    producto_id: int,
    svc: ProductoService = Depends(get_service),
) -> ProductoPublic:
    return svc.get_by_id(producto_id)


@router.patch(
    "/{producto_id}",
    response_model=ProductoPublic,
    summary="Actualizar producto [ADMIN, STOCK]",
)
def update_producto(
    producto_id: int,
    data: ProductoUpdate,
    svc: ProductoService = Depends(get_service),
    _=Depends(require_role(["ADMIN", "STOCK"])),
) -> ProductoPublic:
    return svc.update(producto_id, data)


@router.patch(
    "/{producto_id}/disponibilidad",
    response_model=ProductoPublic,
    summary="Actualizar disponibilidad [ADMIN, STOCK]",
)
def update_disponibilidad(
    producto_id: int,
    data: DisponibilidadUpdate,
    svc: ProductoService = Depends(get_service),
    _=Depends(require_role(["ADMIN", "STOCK"])),
) -> ProductoPublic:
    return svc.actualizar_disponibilidad(producto_id, data)


@router.patch(
    "/{producto_id}/stock",
    response_model=ProductoPublic,
    summary="Actualizar stock [ADMIN, STOCK]",
)
def update_stock(
    producto_id: int,
    data: StockUpdate,
    svc: ProductoService = Depends(get_service),
    _=Depends(require_role(["ADMIN", "STOCK"])),
) -> ProductoPublic:
    return svc.actualizar_stock(producto_id, data)


@router.delete(
    "/{producto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desactivar producto — borrado lógico [ADMIN]",
)
def desactivar_producto(
    producto_id: int,
    svc: ProductoService = Depends(get_service),
    _=Depends(require_role(["ADMIN"])),
) -> None:
    svc.desactivar(producto_id)


@router.patch(
    "/{producto_id}/reactivar",
    response_model=ProductoPublic,
    summary="Reactivar producto [ADMIN]",
)
def reactivar_producto(
    producto_id: int,
    svc: ProductoService = Depends(get_service),
    _=Depends(require_role(["ADMIN"])),
) -> ProductoPublic:
    return svc.reactivar(producto_id)
