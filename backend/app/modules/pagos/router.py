# app/modules/pagos/router.py
"""
Router del módulo pagos — MercadoPago Checkout Pro.

APIRouter() sin prefix (el prefix /api/v1/pagos se aplica en main.py).

Endpoints:
- POST /create-preference  → CLIENT autenticado: crea la preferencia y devuelve init_point.
- POST /webhook            → público (lo llama MercadoPago): procesa la notificación.
- POST /confirm            → CLIENT autenticado: refresca el estado tras el redirect.
- GET  /redirect/{pedido_id}/{status} → redirige al frontend preservando el query string.
"""
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.pagos.schemas import (
    ConfirmarPagoRequest,
    CrearPagoRequest,
    PagoCrearResponse,
    PagoEstadoResponse,
)
from app.modules.pagos.service import PaymentService

router = APIRouter()


def get_service(session: Session = Depends(get_session)) -> PaymentService:
    return PaymentService(session)


@router.post(
    "/create-preference",
    response_model=PagoCrearResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["pagos"],
    summary="Crear preferencia de pago MercadoPago [CLIENT dueño]",
)
def create_preference(
    data: CrearPagoRequest,
    svc: PaymentService = Depends(get_service),
    current=Depends(get_current_user),
) -> PagoCrearResponse:
    """Crea la preferencia de MercadoPago para un pedido PENDIENTE del CLIENT dueño."""
    return svc.crear_pago(data.pedido_id, current)


@router.post(
    "/webhook",
    tags=["pagos"],
    summary="Webhook de MercadoPago [público]",
)
async def webhook(
    request: Request,
    svc: PaymentService = Depends(get_service),
) -> dict:
    """
    Notificación de MercadoPago. Público (lo llama MP, sin cookie de sesión).
    SIEMPRE devuelve 200 — los errores se manejan internamente para no reintentar en MP.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    query_params = dict(request.query_params)
    return await svc.procesar_webhook(body or {}, query_params)


@router.post(
    "/confirm",
    response_model=PagoEstadoResponse,
    tags=["pagos"],
    summary="Refrescar estado del pago tras el redirect [CLIENT autenticado]",
)
async def confirm(
    data: ConfirmarPagoRequest,
    svc: PaymentService = Depends(get_service),
    current=Depends(get_current_user),
) -> PagoEstadoResponse:
    """Refresca el estado del pago desde la página de resultado."""
    return await svc.confirmar_pago(data.pedido_id, data.payment_id, current)


@router.get(
    "/redirect/{pedido_id}/{estado}",
    tags=["pagos"],
    summary="Redirección de MercadoPago al frontend",
)
def redirect(pedido_id: int, estado: str, request: Request) -> RedirectResponse:
    """
    MercadoPago redirige acá tras el checkout (back_urls). Reenviamos al frontend,
    a /pedidos/{id}/pago/{status}, preservando el query string (payment_id, etc.).
    """
    qs = urlencode(dict(request.query_params))
    destino = f"{settings.FRONTEND_URL}/pedidos/{pedido_id}/pago/{estado}"
    if qs:
        destino = f"{destino}?{qs}"
    return RedirectResponse(url=destino, status_code=status.HTTP_303_SEE_OTHER)
