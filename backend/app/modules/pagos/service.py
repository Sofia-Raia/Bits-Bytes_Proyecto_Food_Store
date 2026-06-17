# app/modules/pagos/service.py
"""
Service del módulo pagos — MercadoPago Checkout Pro vía redirect.

Flujo:
1. crear_pago: el CLIENT dueño de un pedido PENDIENTE con forma_pago MERCADOPAGO
   crea una preferencia en MP y obtiene el init_point para redirigir.
2. procesar_webhook: MP notifica el resultado del pago; se consulta el pago real,
   se actualiza el Pago local y, si quedó aprobado, se confirma el pedido (acción
   de sistema) y se emite por WebSocket. SIEMPRE responde 200 a MP.
3. confirmar_pago: refresco manual desde la página de resultado (success/failure/pending).

El SDK de mercadopago se importa de forma PEREZOSA dentro de los métodos para no
acoplar el arranque de la app a la librería ni a la configuración de credenciales.
"""
import uuid
from decimal import Decimal
from typing import Any, Optional

from sqlmodel import Session

from app.core.config import settings
from app.core.exceptions.custom_exceptions import (
    AuthorizationError,
    BusinessRuleError,
    ConflictError,
    ResourceNotFoundError,
)
from app.core.logger import get_logger
from app.core.websocket import manager
from app.modules.pagos.models import Pago
from app.modules.pagos.schemas import PagoCrearResponse, PagoEstadoResponse
from app.modules.pagos.unit_of_work import PagoUnitOfWork
from app.modules.pedidos.repository import PedidoRepository
from app.modules.pedidos.service import PedidoService

logger = get_logger(__name__)

# Estados internos del Pago
ESTADO_PENDIENTE = "pendiente"
ESTADO_APROBADO = "aprobado"
ESTADO_RECHAZADO = "rechazado"


def _map_mp_status(mp_status: Optional[str]) -> str:
    """Mapea el status de MercadoPago al estado interno del Pago."""
    if mp_status == "approved":
        return ESTADO_APROBADO
    if mp_status in {"rejected", "cancelled", "refunded", "charged_back"}:
        return ESTADO_RECHAZADO
    # pending, in_process, authorized, None u otros → pendiente
    return ESTADO_PENDIENTE


class PaymentService:
    """Orquesta la creación de preferencias y el procesamiento de pagos de MercadoPago."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── 1. Crear preferencia de pago ──────────────────────────────────────────

    def crear_pago(self, pedido_id: int, current_user) -> PagoCrearResponse:
        """
        Crea la preferencia de MercadoPago para un pedido PENDIENTE del CLIENT dueño.

        Validaciones:
        - El pedido existe (si no → 404).
        - El pedido pertenece al usuario autenticado (si no → 403).
        - El pedido está en PENDIENTE (si no → 409).
        - MP_ACCESS_TOKEN configurado (si no → 400 "MP no configurado").
        """
        user, _roles = current_user

        with PagoUnitOfWork(self._session) as uow:
            pedido_repo = PedidoRepository(self._session)
            pedido = pedido_repo.get_by_id(pedido_id)
            if not pedido or pedido.deleted_at is not None:
                raise ResourceNotFoundError(f"Pedido con id={pedido_id} no encontrado.")

            if pedido.usuario_id != user.id:
                raise AuthorizationError(
                    "No tenés permiso para pagar un pedido que no es tuyo."
                )

            if pedido.estado_codigo != "PENDIENTE":
                raise ConflictError(
                    f"El pedido no está en estado PENDIENTE (actual: {pedido.estado_codigo})."
                )

            if not settings.MP_ACCESS_TOKEN:
                raise BusinessRuleError("MP no configurado: falta MP_ACCESS_TOKEN.")

            monto: Decimal = pedido.total

            # external_reference único por intento (ERD v7): viaja a MP y permite
            # localizar el Pago al recibir el webhook.
            external_reference = uuid.uuid4().hex

            # ── Crear preferencia en MercadoPago (import perezoso) ──
            import mercadopago  # noqa: PLC0415

            sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)

            base = settings.NGROK_URL or settings.FRONTEND_URL
            preference_data: dict[str, Any] = {
                "items": [
                    {
                        "title": f"Pedido {pedido.codigo}",
                        "quantity": 1,
                        "currency_id": "ARS",
                        "unit_price": float(monto),
                    }
                ],
                "external_reference": external_reference,
                "back_urls": {
                    "success": f"{base}/api/v1/pagos/redirect/{pedido_id}/success",
                    "failure": f"{base}/api/v1/pagos/redirect/{pedido_id}/failure",
                    "pending": f"{base}/api/v1/pagos/redirect/{pedido_id}/pending",
                },
                "auto_return": "approved",
            }
            if settings.MP_WEBHOOK_URL:
                preference_data["notification_url"] = settings.MP_WEBHOOK_URL

            result = sdk.preference().create(preference_data)
            if not isinstance(result, dict) or result.get("status") not in (200, 201):
                resp = result.get("response", {}) if isinstance(result, dict) else {}
                msg = resp.get("message") or resp.get("error") or "error desconocido"
                logger.error("Error creando preferencia MP: %s", result)
                raise BusinessRuleError(f"MercadoPago rechazó la preferencia: {msg}")
            preference = result.get("response", {})
            preference_id = str(preference.get("id", ""))
            init_point = preference.get("init_point") or preference.get("sandbox_init_point")
            
            # ── Persistir el Pago (estado pendiente) ──
            pago = Pago(
                pedido_id=pedido_id,
                monto=monto,
                estado=ESTADO_PENDIENTE,
                external_reference=external_reference,
                mp_preference_id=preference_id or None,
                mp_init_point=init_point,
                idempotency_key=uuid.uuid4().hex,
            )
            uow.pagos.add(pago)
            pago_id = pago.id

        return PagoCrearResponse(
            pago_id=pago_id,
            preference_id=preference_id,
            init_point=init_point,
            public_key=settings.MP_PUBLIC_KEY or None,
        )

    # ── 2. Webhook de MercadoPago ─────────────────────────────────────────────

    async def procesar_webhook(self, data: dict, query_params: dict) -> dict:
        """
        Procesa la notificación de MercadoPago.

        - Extrae el payment_id (soporta type/topic en body o query, y data.id).
        - Consulta el pago real a MP, mapea el estado y actualiza el Pago local.
        - IDEMPOTENCIA: si el Pago ya no está "pendiente", ignora.
        - Si queda "aprobado", confirma el pedido (acción de sistema) y emite WS.
        - SIEMPRE devuelve 200 (nunca propaga una excepción al webhook de MP).
        """
        try:
            topic = (
                data.get("type")
                or data.get("topic")
                or query_params.get("type")
                or query_params.get("topic")
            )
            payment_id = self._extraer_payment_id(data, query_params)

            if topic not in (None, "payment") and payment_id is None:
                # merchant_order u otros sin payment_id → nada que hacer
                logger.info("Webhook MP ignorado (topic=%s sin payment_id)", topic)
                return {"status": "ignored"}

            if payment_id is None:
                logger.info("Webhook MP sin payment_id; se ignora.")
                return {"status": "ignored"}

            if not settings.MP_ACCESS_TOKEN:
                logger.warning("Webhook MP recibido pero MP_ACCESS_TOKEN no configurado.")
                return {"status": "ignored"}

            # ── Consultar el pago real a MercadoPago ──
            import mercadopago  # noqa: PLC0415

            sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
            mp_resp = sdk.payment().get(payment_id)
            payment = mp_resp.get("response", {}) if isinstance(mp_resp, dict) else {}

            if not payment:
                logger.info("Webhook MP: payment_id=%s sin datos en MP.", payment_id)
                return {"status": "ignored"}

            await self._aplicar_resultado_pago(payment, payment_id)
            return {"status": "ok"}

        except Exception as exc:  # noqa: BLE001 — nunca devolver 500 a MP
            logger.error("Error procesando webhook MP (se devuelve 200 igual): %s", exc)
            return {"status": "error_handled"}

    # ── 3. Confirmar / refrescar desde la página de resultado ─────────────────

    async def confirmar_pago(
        self, pedido_id: int, payment_id: Optional[int], current_user
    ) -> PagoEstadoResponse:
        """
        Refresca el estado del pago desde la página de resultado (success/failure/pending).
        Reusa la misma lógica de mapeo/efecto que el webhook.
        """
        if payment_id is not None and settings.MP_ACCESS_TOKEN:
            try:
                import mercadopago  # noqa: PLC0415

                sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
                mp_resp = sdk.payment().get(payment_id)
                payment = mp_resp.get("response", {}) if isinstance(mp_resp, dict) else {}
                if payment:
                    await self._aplicar_resultado_pago(payment, payment_id)
            except Exception as exc:  # noqa: BLE001
                logger.error("Error al refrescar pago pedido=%s: %s", pedido_id, exc)

        # Estado actual del último pago del pedido
        with PagoUnitOfWork(self._session) as uow:
            pago = uow.pagos.get_ultimo_by_pedido(pedido_id)
            estado = pago.estado if pago else None

        return PagoEstadoResponse(estado=estado, pedido_id=pedido_id)

    # ── Helpers internos ──────────────────────────────────────────────────────

    @staticmethod
    def _extraer_payment_id(data: dict, query_params: dict) -> Optional[int]:
        """Extrae el payment_id del body (data.id) o del query (data.id / id)."""
        candidatos = [
            (data.get("data") or {}).get("id"),
            data.get("id") if data.get("type") in ("payment", None) else None,
            query_params.get("data.id"),
            query_params.get("id"),
        ]
        for c in candidatos:
            if c is None:
                continue
            try:
                return int(c)
            except (TypeError, ValueError):
                continue
        return None

    async def _aplicar_resultado_pago(self, payment: dict, payment_id: int) -> None:
        """
        Actualiza el Pago local según el pago de MP y, si quedó aprobado, confirma
        el pedido y emite el evento WebSocket. Idempotente.
        """
        mp_status = payment.get("status")
        mp_status_detail = payment.get("status_detail")
        merchant_order_id = payment.get("order", {}).get("id") if isinstance(payment.get("order"), dict) else None
        external_reference = payment.get("external_reference")
        payment_method_id = payment.get("payment_method_id")
        transaction_amount = payment.get("transaction_amount")
        nuevo_estado = _map_mp_status(mp_status)

        pedido_id_confirmar: Optional[int] = None

        with PagoUnitOfWork(self._session) as uow:
            # Localizar el Pago: mp_payment_id → external_reference → merchant_order.
            # Fallback: si external_reference es numérico, se trata como pedido_id.
            pago = uow.pagos.get_by_mp_payment_id(payment_id)
            if pago is None and external_reference:
                pago = uow.pagos.get_by_external_reference(external_reference)
            if pago is None and merchant_order_id:
                pago = uow.pagos.get_by_mp_merchant_order_id(int(merchant_order_id))
            if pago is None and external_reference and str(external_reference).isdigit():
                pago = uow.pagos.get_ultimo_by_pedido(int(external_reference))

            if pago is None:
                logger.info("Webhook MP: no se encontró Pago local para payment_id=%s.", payment_id)
                return

            # IDEMPOTENCIA: si ya no está pendiente, no reprocesar.
            if pago.estado != ESTADO_PENDIENTE:
                logger.info(
                    "Pago id=%s ya estaba en estado '%s'; se ignora payment_id=%s.",
                    pago.id, pago.estado, payment_id,
                )
                return

            # Actualizar el Pago con los datos de MP
            pago.estado = nuevo_estado
            pago.mp_payment_id = payment_id
            if merchant_order_id:
                pago.mp_merchant_order_id = int(merchant_order_id)
            pago.mp_status = mp_status
            pago.mp_status_detail = mp_status_detail
            pago.payment_method_id = payment_method_id
            if transaction_amount is not None:
                pago.transaction_amount = Decimal(str(transaction_amount))
            from datetime import datetime, timezone
            pago.updated_at = datetime.now(timezone.utc)
            uow.pagos.add(pago)

            if nuevo_estado == ESTADO_APROBADO:
                pedido_id_confirmar = pago.pedido_id

        # ── Confirmar el pedido (acción de sistema) fuera de la tx del Pago ──
        if pedido_id_confirmar is not None:
            pedido_service = PedidoService(self._session)
            try:
                pedido_pub = pedido_service.confirmar_por_pago(
                    pedido_id_confirmar,
                    motivo=f"Pago aprobado por MercadoPago (payment_id={payment_id})",
                )
            except ConflictError as exc:
                # Caso borde: stock se agotó entre crear y pagar. NO propagar al webhook.
                logger.warning(
                    "Pago aprobado pero NO se pudo confirmar el pedido id=%s por stock "
                    "(payment_id=%s): %s. El Pago queda 'aprobado' y el pedido en PENDIENTE; "
                    "requiere revisión del staff.",
                    pedido_id_confirmar, payment_id, exc,
                )
                return

            # ── Emitir WebSocket PEDIDO_CONFIRMADO ──
            import json
            pedido_dict = json.loads(pedido_pub.model_dump_json())
            await manager.broadcast_to_order(
                pedido_id_confirmar, "PEDIDO_CONFIRMADO", pedido_dict
            )
            await manager.broadcast_to_roles(
                ["PEDIDOS", "ADMIN"], "PEDIDO_CONFIRMADO", pedido_dict
            )
