# app/modules/pedidos/router.py
"""
Router del módulo pedidos.
WebSockets (tiempo real):
- Endpoint /ws con handshake por cookie JWT; rooms por rol y por pedido.
- create_pedido y avanzar_estado son async para poder hacer await del broadcast WS.
- Emisión de eventos NUEVO_PEDIDO y PEDIDO_{ESTADO} tras cada cambio de estado.
"""
from typing import Annotated, List

from fastapi import (
    APIRouter, Depends, HTTPException, Query, WebSocket,
    WebSocketDisconnect, status,
)
from jose import JWTError
from sqlmodel import Session

from app.core.config import settings
from app.core.database import engine, get_session
from app.core.pagination import Paginated, paginar, offset_de
from app.core.websocket import manager
from app.modules.auth.dependencies import get_current_user, require_admin, require_role
from app.modules.auth.repository import AuthRepository
from app.modules.auth.security import decode_token
from app.modules.pedidos.repository import CatalogoRepository, PedidoRepository
from app.modules.pedidos.schemas import (
    AvanzarEstadoRequest,
    FormaPagoPublic,
    HistorialPublic,
    PedidoCreate,
    PedidoConfigPublic,
    PedidoList,
    PedidoPublic,
    PedidoUpdate,
)
from app.modules.pedidos.service import PedidoService

router = APIRouter()

# Mapeo estado destino → nombre del evento WS
def get_service(session: Session = Depends(get_session)) -> PedidoService:
    return PedidoService(session)


# ── Catálogo ──────────────────────────────────────────────────────────────────

# GET /formas-pago público (necesario para checkout sin login previo)
@router.get(
    "/formas-pago",
    response_model=List[FormaPagoPublic],
    summary="Formas de pago habilitadas [público]",
)
def list_formas_pago(
    session: Session = Depends(get_session),
) -> List[FormaPagoPublic]:
    repo = CatalogoRepository(session)
    return [FormaPagoPublic.model_validate(f) for f in repo.get_formas_pago_habilitadas()]


# GET /config público: expone parámetros del checkout (costo de envío) para que
# el frontend muestre el mismo monto que el backend cobra. Fuente de verdad única.
@router.get(
    "/config",
    response_model=PedidoConfigPublic,
    summary="Parámetros de checkout (costo de envío) [público]",
)
def get_pedido_config() -> PedidoConfigPublic:
    return PedidoConfigPublic(costo_envio=settings.COSTO_ENVIO)


# ── CRUD Pedidos ──────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=PedidoPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pedido [AUTH]",
)
async def create_pedido(
    data: PedidoCreate,
    svc: PedidoService = Depends(get_service),
    current=Depends(get_current_user),
) -> PedidoPublic:
    """
    Crea un pedido. Async para poder hacer await del broadcast WS tras crear.

    Resolución de usuario_id efectivo :
    - Si data.usuario_id es None o igual al propio → se usa el del JWT.
    - Si data.usuario_id apunta a otro usuario:
        * Caller tiene ADMIN o PEDIDOS → se permite (crear para otro).
        * Caller es CLIENT → 403.
    """
    user, roles = current

    if data.usuario_id is not None and data.usuario_id != user.id:
        # Intento de crear en nombre de otro usuario
        if not any(r in {"ADMIN", "PEDIDOS"} for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para crear pedidos en nombre de otros usuarios.",
            )
        usuario_id_efectivo = data.usuario_id
    else:
        usuario_id_efectivo = user.id

    result = await svc.create(data, usuario_id_efectivo, roles)
    return result


@router.get(
    "/",
    response_model=Paginated[PedidoPublic],
    summary="Listar pedidos activos (paginado) [AUTH]",
)
def list_pedidos(
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    estado: Annotated[str | None, Query(max_length=20)] = None,
    busqueda: Annotated[str | None, Query(max_length=20)] = None,
    svc: PedidoService = Depends(get_service),
    current=Depends(get_current_user),
) -> Paginated[PedidoPublic]:
    """
    Lista pedidos activos.
    si el caller solo tiene rol CLIENT, devuelve únicamente sus propios pedidos.
    Filtros opcionales: estado (FSM) y busqueda (por código de pedido).
    """
    user, roles = current
    estado_norm = estado.strip().upper() if estado and estado.strip() else None
    busqueda_norm = busqueda.strip() if busqueda and busqueda.strip() else None
    result: PedidoList = svc.get_all(
        offset=offset_de(page, size), limit=size, usuario_id=user.id, roles=roles,
        estado=estado_norm, busqueda=busqueda_norm,
    )
    return paginar(result.data, result.total, page, size)


@router.get(
    "/{pedido_id}",
    response_model=PedidoPublic,
    summary="Obtener pedido por ID [AUTH]",
)
def get_pedido(
    pedido_id: int,
    svc: PedidoService = Depends(get_service),
    current=Depends(get_current_user),
) -> PedidoPublic:
    """
     CLIENT-only solo puede ver sus propios pedidos (ownership check en service).
    """
    user, roles = current
    return svc.get_by_id(pedido_id, usuario_id=user.id, roles=roles)


@router.patch(
    "/{pedido_id}",
    response_model=PedidoPublic,
    summary="Editar pedido PENDIENTE [AUTH]",
)
def update_pedido(
    pedido_id: int,
    data: PedidoUpdate,
    svc: PedidoService = Depends(get_service),
    current=Depends(get_current_user),
) -> PedidoPublic:
    """
    edita un pedido en estado PENDIENTE.
    CLIENT solo puede editar sus propios pedidos.
    ADMIN/PEDIDOS pueden editar cualquier pedido.
    Siempre inserta entrada de historial con motivo 'Modificación de pedido'.
    """
    user, roles = current
    return svc.update(pedido_id, data, usuario_id=user.id, roles=roles)


@router.delete(
    "/{pedido_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete de pedido [ADMIN]",
)
def delete_pedido(
    pedido_id: int,
    svc: PedidoService = Depends(get_service),
    _=Depends(require_admin),
) -> None:
    svc.soft_delete(pedido_id)


# ── FSM ───────────────────────────────────────────────────────────────────────

@router.patch(
    "/{pedido_id}/estado",
    response_model=PedidoPublic,
    summary="Avanzar estado del pedido (FSM) [AUTH]",
)
async def avanzar_estado(
    pedido_id: int,
    data: AvanzarEstadoRequest,
    svc: PedidoService = Depends(get_service),
    current=Depends(get_current_user),
) -> PedidoPublic:
    """
    Async para poder hacer await del broadcast WS tras cada transición.

    usuario_id del JWT, nunca del body.
    el service verifica permisos según PERMISOS_TRANSICION.
    decremento/restauración de stock según transición.
    """
    user, roles = current
    result = await svc.avanzar_estado(pedido_id, data, usuario_id=user.id, roles=roles)

    return result


# ── Historial ─────────────────────────────────────────────────────────────────

@router.get(
    "/{pedido_id}/historial",
    response_model=List[HistorialPublic],
    summary="Historial de estados del pedido [AUTH]",
)
def get_historial(
    pedido_id: int,
    svc: PedidoService = Depends(get_service),
    _=Depends(get_current_user),
) -> List[HistorialPublic]:
    """
     endpoint se mantiene en router de pedidos; internamente delega
    a HistorialService.get_by_pedido() vía PedidoService.get_historial().
    """
    return svc.get_historial(pedido_id)


# ── WebSocket ─────────────────────────────────────────────────────────────────

@router.websocket("/ws")
async def pedidos_ws(ws: WebSocket) -> None:
    """
    Endpoint WebSocket de pedidos — /api/v1/pedidos/ws.

    Handshake: lee la cookie access_token, decodifica el JWT y busca el usuario en DB.
    Cierra con 1008 (Policy Violation) si la autenticación falla.

    Rooms al conectar:
    - ADMIN  → room "role:ADMIN"
    - PEDIDOS → room "role:PEDIDOS"
    - CLIENT  → room "role:CLIENT"
    - STOCK   → no se conecta (el endpoint lo acepta pero no lo une a ninguna room útil)

    Mensajes del cliente:
    - {"action":"subscribe-order","order_id":N}   → une a "order:N"
      CLIENT: verifica que el pedido le pertenezca antes de suscribir.
    - {"action":"unsubscribe-order","order_id":N} → sale de "order:N"
    """
    # ── 1. Aceptar SIEMPRE primero (protocolo WebSocket requiere accept antes de close) ──
    await ws.accept()

    # ── 2. Leer y validar token ──
    token = ws.cookies.get("access_token")
    if not token:
        await ws.close(code=1008, reason="Sin autenticación: falta cookie access_token")
        return

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("tipo de token incorrecto")
        email: str = payload.get("sub", "")
        if not email:
            raise ValueError("sub vacío en el token")
    except (JWTError, ValueError) as exc:
        await ws.close(code=1008, reason=f"Token inválido: {exc}")
        return

    # ── 3. Buscar usuario activo y sus roles en DB ──
    with Session(engine) as db:
        repo = AuthRepository(db)
        user = repo.get_active_by_email(email)
        if not user:
            await ws.close(code=1008, reason="Usuario no encontrado o inactivo")
            return
        roles = repo.get_roles(user.id)

    # ── 4. Registrar en el manager y unir a rooms de rol ──
    manager.connect(ws, roles)

    is_client_only = (
        "CLIENT" in roles
        and not any(r in {"ADMIN", "PEDIDOS"} for r in roles)
    )

    # Confirmar conexión al cliente
    await ws.send_json({"event": "WS_CONNECTED", "data": {"user_id": user.id, "roles": roles}})

    # ── 5. Bucle de mensajes ──
    try:
        while True:
            try:
                data = await ws.receive_json()
            except Exception:
                break  # conexión cerrada

            action = data.get("action")
            order_id = data.get("order_id")

            if action == "subscribe-order" and isinstance(order_id, int):
                # CLIENT: verificar que el pedido le pertenece
                if is_client_only:
                    with Session(engine) as db:
                        repo_p = PedidoRepository(db)
                        pedido = repo_p.get_by_id(order_id)
                        if not pedido or pedido.usuario_id != user.id:
                            await ws.send_json({
                                "event": "ERROR",
                                "data": {
                                    "message": "Pedido no encontrado o no pertenece al usuario",
                                    "order_id": order_id,
                                },
                            })
                            continue  # no suscribir
                # Staff puede suscribirse a cualquier pedido
                manager.join_order_room(ws, order_id)
                await ws.send_json({
                    "event": "SUBSCRIBED",
                    "data": {"order_id": order_id},
                })

            elif action == "unsubscribe-order" and isinstance(order_id, int):
                manager.leave_order_room(ws, order_id)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect(ws)
