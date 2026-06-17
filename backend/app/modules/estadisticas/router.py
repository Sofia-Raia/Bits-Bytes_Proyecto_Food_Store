# app/modules/estadisticas/router.py
"""Endpoints GET /api/v1/estadisticas/*. Solo ADMIN."""
from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.database import get_session
from app.modules.auth.dependencies import require_role
from app.modules.estadisticas.schemas import (
    IngresosResponse, PedidosEstadoItem,
    ProductoTopItem, ResumenResponse, VentasPeriodoItem,
)
from app.modules.estadisticas.service import EstadisticasService

router = APIRouter()
_ADMIN = Depends(require_role(["ADMIN"]))


def get_svc(session: Session = Depends(get_session)) -> EstadisticasService:
    return EstadisticasService(session)


def _defaults() -> tuple[date, date]:
    hasta = date.today()
    return hasta - timedelta(days=29), hasta


@router.get("/resumen", response_model=ResumenResponse, summary="KPIs del negocio [ADMIN]")
def resumen(svc: EstadisticasService = Depends(get_svc), _=_ADMIN) -> ResumenResponse:
    return svc.resumen()


@router.get("/ventas", response_model=List[VentasPeriodoItem], summary="Ventas por período [ADMIN]")
def ventas(
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    agrupacion: str = Query(default="day", pattern="^(day|week|month)$"),
    svc: EstadisticasService = Depends(get_svc),
    _=_ADMIN,
) -> List[VentasPeriodoItem]:
    d, h = _defaults()
    return svc.ventas_periodo(desde or d, hasta or h, agrupacion)


@router.get("/productos-top", response_model=List[ProductoTopItem], summary="Top productos [ADMIN]")
def productos_top(
    limit: int = Query(default=10, ge=1, le=50),
    svc: EstadisticasService = Depends(get_svc),
    _=_ADMIN,
) -> List[ProductoTopItem]:
    return svc.productos_top(limit)


@router.get("/pedidos-por-estado", response_model=List[PedidosEstadoItem], summary="Distribución por estado [ADMIN]")
def pedidos_por_estado(svc: EstadisticasService = Depends(get_svc), _=_ADMIN) -> List[PedidosEstadoItem]:
    return svc.pedidos_por_estado()


@router.get("/ingresos", response_model=IngresosResponse, summary="Ingresos por forma de pago [ADMIN]")
def ingresos(
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    svc: EstadisticasService = Depends(get_svc),
    _=_ADMIN,
) -> IngresosResponse:
    d, h = _defaults()
    return svc.ingresos_por_forma_pago(desde or d, hasta or h)
