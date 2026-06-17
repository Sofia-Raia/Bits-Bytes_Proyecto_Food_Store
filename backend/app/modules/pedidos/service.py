# app/modules/pedidos/service.py
"""
Service del módulo pedidos.


Stock desde ingredientes:
- create():         validación split TERMINADO/MANUFACTURADO.
- avanzar_estado(): decremento/restauración split TERMINADO/MANUFACTURADO.
- soft_delete():    restauración split TERMINADO/MANUFACTURADO.

 Modificar pedido PENDIENTE :
- update(): solo permite editar pedidos PENDIENTE, verifica ownership,
  reemplaza ítems, recalcula totales, inserta entrada de historial.

Decimal:
- Toda la aritmética monetaria usa Decimal para evitar errores de punto flotante.
  costo_envio = settings.COSTO_ENVIO, descuento = Decimal("0.00"), etc.
"""
import json
from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Session

from app.core.codigo import generar_codigo
from app.core.config import settings
from app.core.websocket import manager
from app.core.exceptions.custom_exceptions import (
    AuthorizationError,
    BusinessRuleError,
    ConflictError,
    ResourceNotFoundError,
    ValidationError,
)
from app.modules.historial_estados_pedido.models import HistorialEstadoPedido
from app.modules.historial_estados_pedido.schemas import HistorialPublic
from app.modules.historial_estados_pedido.service import HistorialService
from app.modules.pedidos.models import DetallePedido, Pedido
from app.modules.pedidos.schemas import (
    AvanzarEstadoRequest,
    DetallePedidoPublic,
    PedidoCreate,
    PedidoList,
    PedidoPublic,
    PedidoUpdate,
)
from app.modules.pedidos.unit_of_work import PedidoUnitOfWork
from app.modules.productos.models import TipoProducto
from app.modules.usuarios.models import Usuario

_QUANT = Decimal("0.01")

# Mapa estado destino → evento WebSocket que se emite tras la transición (RN-06).
_EVENTO_POR_ESTADO: dict[str, str] = {
    "CONFIRMADO": "PEDIDO_CONFIRMADO",
    "EN_PREP":    "PEDIDO_EN_PREP",
    "ENTREGADO":  "PEDIDO_ENTREGADO",
    "CANCELADO":  "PEDIDO_CANCELADO",
}

# ── FSM ───────────────────────────────────────────────────────────────────────
_ESTADOS_STOCK_DECREMENTADO = {"CONFIRMADO", "EN_PREP"}

PERMISOS_TRANSICION: dict[tuple[str, str], list[str]] = {
    ("PENDIENTE",  "CONFIRMADO"): ["PEDIDOS", "ADMIN"],
    ("PENDIENTE",  "CANCELADO"):  ["CLIENT_OWNER", "PEDIDOS", "ADMIN"],
    ("CONFIRMADO", "EN_PREP"):    ["PEDIDOS", "ADMIN"],
    ("CONFIRMADO", "CANCELADO"):  ["CLIENT_OWNER", "PEDIDOS", "ADMIN"],  # BACKEND-4
    ("EN_PREP",    "ENTREGADO"):  ["PEDIDOS", "ADMIN"],
    ("EN_PREP",    "CANCELADO"):  ["ADMIN"],
}


def _check_permiso_transicion(
    pedido: Pedido,
    estado_actual: str,
    estado_hacia: str,
    usuario_id: int,
    roles: list[str],
) -> None:
    key = (estado_actual, estado_hacia)
    permitidos = PERMISOS_TRANSICION.get(key)

    if permitidos is None:
        posibles = [d for (o, d) in PERMISOS_TRANSICION if o == estado_actual]
        raise ValidationError(
            f"Transición inválida: {estado_actual} → {estado_hacia}. "
            f"Transiciones permitidas desde '{estado_actual}': "
            f"{posibles or ['ninguna (estado terminal)']}"
        )

    has_permission = False
    for rol in permitidos:
        if rol == "CLIENT_OWNER":
            if "CLIENT" in roles and pedido.usuario_id == usuario_id:
                has_permission = True
                break
        elif rol in roles:
            has_permission = True
            break

    if not has_permission:
        raise AuthorizationError(
            f"No tienes permiso para la transición {estado_actual} → {estado_hacia}."
        )


class PedidoService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_or_404(self, uow: PedidoUnitOfWork, pedido_id: int) -> Pedido:
        pedido = uow.pedidos.get_by_id(pedido_id)
        if not pedido or pedido.deleted_at is not None:
            raise ResourceNotFoundError(f"Pedido con id={pedido_id} no encontrado.")
        return pedido

    def _build_public(self, uow: PedidoUnitOfWork, pedido: Pedido) -> PedidoPublic:
        detalles = uow.pedidos.get_detalles(pedido.id)
        historial = uow.historial.get_by_pedido(pedido.id)
        usuario = self._session.get(Usuario, pedido.usuario_id)
        return PedidoPublic(
            id=pedido.id,
            codigo=pedido.codigo,
            usuario_id=pedido.usuario_id,
            usuario_nombre=f"{usuario.nombre} {usuario.apellido}" if usuario else None,
            direccion_id=pedido.direccion_id,
            direccion_snapshot=pedido.direccion_snapshot,
            estado_codigo=pedido.estado_codigo,
            forma_pago_codigo=pedido.forma_pago_codigo,
            subtotal=pedido.subtotal,
            descuento=pedido.descuento,
            costo_envio=pedido.costo_envio,
            total=pedido.total,
            notas=pedido.notas,
            detalles=[
                DetallePedidoPublic(
                    pedido_id=d.pedido_id,
                    producto_id=d.producto_id,
                    cantidad=d.cantidad,
                    nombre_snapshot=d.nombre_snapshot,
                    precio_snapshot=d.precio_snapshot,
                    subtotal_snap=d.subtotal_snap,
                    personalizacion=d.personalizacion,
                    created_at=d.created_at,
                )
                for d in detalles
            ],
            historial=[
                HistorialPublic(
                    id=h.id,
                    pedido_id=h.pedido_id,
                    estado_desde=h.estado_desde,
                    estado_hacia=h.estado_hacia,
                    usuario_id=h.usuario_id,
                    motivo=h.motivo,
                    created_at=h.created_at,
                )
                for h in historial
            ],
            created_at=pedido.created_at,
            updated_at=pedido.updated_at,
        )

    def _validar_stock_items(self, uow: PedidoUnitOfWork, items) -> list[tuple]:
        """
        Valida stock para cada ítem y retorna lista de (item, prod, subtotal_item).
        Split TERMINADO / MANUFACTURADO .
        """
        items_validados: list[tuple] = []

        for item in items:
            prod = uow.productos.get_by_id_for_update(item.producto_id)
            if not prod or prod.deleted_at is not None:
                raise ResourceNotFoundError(f"Producto con id={item.producto_id} no encontrado.")
            if not prod.disponible:
                raise ConflictError(f"El producto '{prod.nombre}' no está disponible.")

            if prod.tipo == TipoProducto.TERMINADO:
                # TERMINADO: validar stock directo del producto
                if prod.stock_cantidad < item.cantidad:
                    raise ConflictError(
                        f"Stock insuficiente para '{prod.nombre}'. "
                        f"Disponible: {prod.stock_cantidad}, solicitado: {item.cantidad}."
                    )
            else:
                # MANUFACTURADO: validar stock de cada ingrediente de la receta
                pi_list = uow.productos.get_producto_ingredientes(prod.id)
                personalizacion = getattr(item, "personalizacion", None) or []
                for pi in pi_list:
                    if pi.ingrediente_id in personalizacion:
                        if not pi.es_removible:
                            raise ValidationError(
                                f"El ingrediente id={pi.ingrediente_id} no es removible "
                                f"en '{prod.nombre}'."
                            )
                        continue  # saltear: el cliente lo removió
                    ingrediente = uow.ingredientes.get_by_id_for_update(pi.ingrediente_id)
                    if not ingrediente or ingrediente.deleted_at:
                        raise ResourceNotFoundError(f"Ingrediente id={pi.ingrediente_id} no encontrado.")
                    necesario = pi.cantidad * item.cantidad
                    if ingrediente.stock_cantidad < necesario:
                        raise ConflictError(
                            f"Stock insuficiente de '{ingrediente.nombre}' "
                            f"para '{prod.nombre}'. "
                            f"Disponible: {float(ingrediente.stock_cantidad):.3f}, "
                            f"necesario: {float(necesario):.3f}."
                        )

            subtotal_item = (prod.precio_base * item.cantidad).quantize(_QUANT)
            items_validados.append((item, prod, subtotal_item))

        return items_validados

    # ── Crear pedido ──────────────────────────────────────────────────────────

    async def create(
        self,
        data: PedidoCreate,
        usuario_id: int,   #  del JWT, resuelto con opción-c en router 
        roles: list[str],
    ) -> PedidoPublic:
        """
        Crea un pedido de forma atómica (RN-PE01).
        Toda la aritmética usa Decimal para evitar errores de punto flotante.
        """
        with PedidoUnitOfWork(self._session) as uow:
            # 1. Validar forma de pago
            forma = uow.catalogos.get_forma_pago(data.forma_pago_codigo)
            if not forma or not forma.habilitado:
                raise BusinessRuleError(
                    f"Forma de pago '{data.forma_pago_codigo}' no válida o deshabilitada."
                )

            # 2. Validar productos y calcular subtotal (T3.6: split TERMINADO/MANUFACTURADO)
            items_validados = self._validar_stock_items(uow, data.items)
            subtotal = sum(iv[2] for iv in items_validados).quantize(_QUANT)

            # 3. Calcular descuento y costo_envio — Decimal fijos
            descuento   = Decimal("0.00")
            costo_envio = settings.COSTO_ENVIO if data.direccion_id is not None else Decimal("0.00")
            total       = (subtotal - descuento + costo_envio).quantize(_QUANT)

            # 4. Snapshot de dirección
            direccion_snapshot: str | None = None
            usuario_id_efectivo = usuario_id  # ya resuelto por el router
            if data.direccion_id:
                direccion = uow.direcciones.get_by_id_y_usuario(
                    data.direccion_id, usuario_id_efectivo
                )
                if not direccion:
                    raise ResourceNotFoundError(
                        "Dirección no encontrada o no pertenece al usuario."
                    )
                direccion_snapshot = json.dumps({
                    "alias":           direccion.alias,
                    "linea1":          direccion.linea1,
                    "linea2":          direccion.linea2,
                    "ciudad":          direccion.ciudad,
                    "provincia":       direccion.provincia,
                    "codigo_postal":   direccion.codigo_postal,
                })

            # 5. Persistir pedido
            codigo = generar_codigo(self._session, "pedido")
            pedido = Pedido(
                codigo=codigo,
                usuario_id=usuario_id_efectivo,
                direccion_id=data.direccion_id,
                direccion_snapshot=direccion_snapshot,
                forma_pago_codigo=data.forma_pago_codigo,
                estado_codigo="PENDIENTE",
                subtotal=subtotal,
                descuento=descuento,
                costo_envio=costo_envio,
                total=total,
                notas=data.notas,
            )
            uow.pedidos.add(pedido)

            # 6. Detalles
            for item, prod, subtotal_item in items_validados:
                uow.pedidos.add_detalle(DetallePedido(
                    pedido_id=pedido.id,
                    producto_id=prod.id,
                    cantidad=item.cantidad,
                    nombre_snapshot=prod.nombre,
                    precio_snapshot=prod.precio_base,
                    subtotal_snap=subtotal_item,
                    personalizacion=item.personalizacion,
                ))

            # 7. Historial inicial
            uow.historial.add(HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_desde=None,
                estado_hacia="PENDIENTE",
                usuario_id=usuario_id_efectivo,
            ))

            result = self._build_public(uow, pedido)

        # ── Broadcast WS post-commit (RN-06): fuera del bloque UoW ──
        pedido_dict = json.loads(result.model_dump_json())
        await manager.broadcast_to_roles(["PEDIDOS", "ADMIN"], "NUEVO_PEDIDO", pedido_dict)
        await manager.broadcast_to_order(result.id, "NUEVO_PEDIDO", pedido_dict)
        return result

    # ── Listar / obtener ──────────────────────────────────────────────────────

    def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        usuario_id: int = 0,
        roles: list[str] | None = None,
        estado: str | None = None,
        busqueda: str | None = None,
    ) -> PedidoList:
        roles = roles or []
        is_client_only = (
            "CLIENT" in roles
            and not any(r in {"ADMIN", "PEDIDOS"} for r in roles)
        )
        with PedidoUnitOfWork(self._session) as uow:
            if is_client_only:
                pedidos = uow.pedidos.get_all_by_usuario(
                    usuario_id, offset=offset, limit=limit,
                    estado=estado, busqueda=busqueda,
                )
                total = uow.pedidos.count_by_usuario(
                    usuario_id, estado=estado, busqueda=busqueda
                )
            else:
                pedidos = uow.pedidos.get_all_activos(
                    offset=offset, limit=limit, estado=estado, busqueda=busqueda
                )
                total = uow.pedidos.count_activos(estado=estado, busqueda=busqueda)
            result = PedidoList(
                data=[self._build_public(uow, p) for p in pedidos],
                total=total,
            )
        return result

    def get_by_id(
        self,
        pedido_id: int,
        usuario_id: int,
        roles: list[str],
    ) -> PedidoPublic:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)
            is_client_only = (
                "CLIENT" in roles
                and not any(r in {"ADMIN", "PEDIDOS"} for r in roles)
            )
            if is_client_only and pedido.usuario_id != usuario_id:
                raise AuthorizationError("No tienes permiso para ver este pedido.")
            result = self._build_public(uow, pedido)
        return result

    def update(
        self,
        pedido_id: int,
        data: PedidoUpdate,
        usuario_id: int,
        roles: list[str],
    ) -> PedidoPublic:
        """
        Edita un pedido en estado PENDIENTE.
        - Solo pedidos PENDIENTE.
        - CLIENT solo puede editar sus propios pedidos.
        - ADMIN/PEDIDOS pueden editar cualquiera.
        - Si se envían items: reemplaza detalles y revalida stock.
        - Siempre inserta entrada de historial (D5: excepción permitida).
        """
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)

            # Solo PENDIENTE
            if pedido.estado_codigo != "PENDIENTE":
                raise ConflictError("Solo se pueden modificar pedidos en estado PENDIENTE.")

            # Verificar ownership si es CLIENT
            is_client_only = (
                "CLIENT" in roles
                and not any(r in {"ADMIN", "PEDIDOS"} for r in roles)
            )
            if is_client_only and pedido.usuario_id != usuario_id:
                raise AuthorizationError("No tenés permiso para modificar este pedido.")

            # Reemplazar ítems si se enviaron
            if data.items is not None:
                items_validados = self._validar_stock_items(uow, data.items)
                subtotal = sum(iv[2] for iv in items_validados).quantize(_QUANT)
                costo_envio = settings.COSTO_ENVIO if (
                    data.direccion_id if data.direccion_id is not None else pedido.direccion_id
                ) is not None else Decimal("0.00")
                total = (subtotal - pedido.descuento + costo_envio).quantize(_QUANT)

                # Borrar detalles viejos
                uow.pedidos.delete_detalles(pedido.id)

                # Insertar detalles nuevos
                for item, prod, subtotal_item in items_validados:
                    uow.pedidos.add_detalle(DetallePedido(
                        pedido_id=pedido.id,
                        producto_id=prod.id,
                        cantidad=item.cantidad,
                        nombre_snapshot=prod.nombre,
                        precio_snapshot=prod.precio_base,
                        subtotal_snap=subtotal_item,
                        personalizacion=item.personalizacion,
                    ))

                pedido.subtotal    = subtotal
                pedido.costo_envio = costo_envio
                pedido.total       = total

            # Actualizar dirección
            if data.direccion_id is not None and data.direccion_id != pedido.direccion_id:
                direccion = uow.direcciones.get_by_id_y_usuario(
                    data.direccion_id, pedido.usuario_id
                )
                if not direccion:
                    raise ResourceNotFoundError(
                        "Dirección no encontrada o no pertenece al usuario del pedido."
                    )
                pedido.direccion_id = data.direccion_id
                pedido.direccion_snapshot = json.dumps({
                    "alias":         direccion.alias,
                    "linea1":        direccion.linea1,
                    "linea2":        direccion.linea2,
                    "ciudad":        direccion.ciudad,
                    "provincia":     direccion.provincia,
                    "codigo_postal": direccion.codigo_postal,
                })
                # Recalcular costo_envio si items no vino en este request
                if data.items is None:
                    pedido.costo_envio = settings.COSTO_ENVIO
                    pedido.total = (pedido.subtotal - pedido.descuento + pedido.costo_envio).quantize(_QUANT)

            # Actualizar forma de pago
            if data.forma_pago_codigo is not None:
                forma = uow.catalogos.get_forma_pago(data.forma_pago_codigo)
                if not forma or not forma.habilitado:
                    raise BusinessRuleError(
                        f"Forma de pago '{data.forma_pago_codigo}' no válida."
                    )
                pedido.forma_pago_codigo = data.forma_pago_codigo

            # Actualizar notas
            if data.notas is not None:
                pedido.notas = data.notas

            pedido.updated_at = datetime.now(timezone.utc)
            uow.pedidos.add(pedido)

            # Historial ( excepción — PENDIENTE→PENDIENTE para modificaciones)
            uow.historial.add(HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_desde="PENDIENTE",
                estado_hacia="PENDIENTE",
                usuario_id=usuario_id,
                motivo="Modificación de pedido",
            ))

            result = self._build_public(uow, pedido)
        return result

    # ── Avanzar estado (FSM) ──────────────────────────────────────────────────

    async def avanzar_estado(
        self,
        pedido_id: int,
        data: AvanzarEstadoRequest,
        usuario_id: int,
        roles: list[str],
    ) -> PedidoPublic:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)
            estado_actual = pedido.estado_codigo
            estado_hacia  = data.estado_hacia

            _check_permiso_transicion(pedido, estado_actual, estado_hacia, usuario_id, roles)

            if estado_hacia in {"CANCELADO", "CONFIRMADO"} and not data.motivo:
                raise ValidationError(
                    f"El campo 'motivo' es requerido para la transición → {estado_hacia}."
                )

            # Decremento de stock al confirmar
            if estado_actual == "PENDIENTE" and estado_hacia == "CONFIRMADO":
                detalles = uow.pedidos.get_detalles(pedido.id)
                for detalle in detalles:
                    prod = uow.productos.get_by_id_for_update(detalle.producto_id)
                    if not prod:
                        raise ResourceNotFoundError(
                            f"Producto id={detalle.producto_id} no encontrado al confirmar."
                        )

                    if prod.tipo == TipoProducto.TERMINADO:
                        if prod.stock_cantidad < detalle.cantidad:
                            raise ConflictError(
                                f"Stock insuficiente para '{prod.nombre}' al confirmar. "
                                f"Disponible: {prod.stock_cantidad}, requerido: {detalle.cantidad}."
                            )
                        prod.stock_cantidad -= detalle.cantidad
                        uow.productos.add(prod)
                    else:
                        # MANUFACTURADO: descontar ingredientes
                        pi_list = uow.productos.get_producto_ingredientes(prod.id)
                        personalizacion = detalle.personalizacion or []
                        for pi in pi_list:
                            if pi.ingrediente_id in personalizacion:
                                continue  # saltear removidos
                            ingrediente = uow.ingredientes.get_by_id_for_update(pi.ingrediente_id)
                            if not ingrediente:
                                continue
                            necesario = pi.cantidad * detalle.cantidad
                            if ingrediente.stock_cantidad < necesario:
                                raise ConflictError(
                                    f"Stock insuficiente de '{ingrediente.nombre}' "
                                    f"al confirmar '{prod.nombre}'."
                                )
                            ingrediente.stock_cantidad -= necesario
                            uow.ingredientes.add(ingrediente)

            # Restauración de stock al cancelar
            elif estado_hacia == "CANCELADO" and estado_actual in _ESTADOS_STOCK_DECREMENTADO:
                detalles = uow.pedidos.get_detalles(pedido.id)
                for detalle in detalles:
                    prod = uow.productos.get_by_id(detalle.producto_id)
                    if not prod:
                        continue

                    if prod.tipo == TipoProducto.TERMINADO:
                        prod.stock_cantidad += detalle.cantidad
                        uow.productos.add(prod)
                    else:
                        # MANUFACTURADO: restituir solo lo que se descontó
                        pi_list = uow.productos.get_producto_ingredientes(prod.id)
                        personalizacion = detalle.personalizacion or []
                        for pi in pi_list:
                            if pi.ingrediente_id in personalizacion:
                                continue  # D6: no se descontó, no se restituye
                            ingrediente = uow.ingredientes.get_by_id(pi.ingrediente_id)
                            if not ingrediente:
                                continue
                            necesario = pi.cantidad * detalle.cantidad
                            ingrediente.stock_cantidad += necesario
                            uow.ingredientes.add(ingrediente)

            pedido.estado_codigo = estado_hacia
            pedido.updated_at    = datetime.now(timezone.utc)
            uow.pedidos.add(pedido)

            uow.historial.add(HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_desde=estado_actual,
                estado_hacia=estado_hacia,
                usuario_id=usuario_id,
                motivo=data.motivo,
            ))

            result = self._build_public(uow, pedido)

        # ── Broadcast WS post-commit (RN-06): fuera del bloque UoW ──
        evento = _EVENTO_POR_ESTADO.get(data.estado_hacia, "PEDIDO_ACTUALIZADO")
        pedido_dict = json.loads(result.model_dump_json())
        await manager.broadcast_to_roles(["PEDIDOS", "ADMIN"], evento, pedido_dict)
        await manager.broadcast_to_order(pedido_id, evento, pedido_dict)
        return result

    # ── Confirmación de sistema por pago aprobado ────────────────────

    def confirmar_por_pago(self, pedido_id: int, motivo: str) -> PedidoPublic:
        """
        Ejecuta la transición PENDIENTE→CONFIRMADO como ACCIÓN DE SISTEMA,
        disparada por un pago aprobado de MercadoPago (no por un usuario).

        Reusa el MISMO decremento de stock (TERMINADO/MANUFACTURADO) y el MISMO
        registro de historial que avanzar_estado, pero BYPASSEA la matriz de roles
        (PERMISOS_TRANSICION): no hay usuario humano detrás de la confirmación.

        - Si el pedido no existe → ResourceNotFoundError (404).
        - Si el pedido NO está en PENDIENTE (idempotencia / doble webhook) → no hace
          nada y devuelve el estado actual sin error.
        - Si falta stock (se agotó entre crear el pedido y pagar) → ConflictError,
          que el PaymentService captura para dejar el pedido en PENDIENTE y avisar al staff.

        No modifica avanzar_estado ni la matriz _TRANSICIONES.
        """
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)
            estado_actual = pedido.estado_codigo

            # Idempotencia: si ya no está PENDIENTE, no re-confirmar ni re-descontar.
            if estado_actual != "PENDIENTE":
                return self._build_public(uow, pedido)

            # Decremento de stock al confirmar (misma lógica que avanzar_estado)
            detalles = uow.pedidos.get_detalles(pedido.id)
            for detalle in detalles:
                prod = uow.productos.get_by_id_for_update(detalle.producto_id)
                if not prod:
                    raise ResourceNotFoundError(
                        f"Producto id={detalle.producto_id} no encontrado al confirmar."
                    )

                if prod.tipo == TipoProducto.TERMINADO:
                    if prod.stock_cantidad < detalle.cantidad:
                        raise ConflictError(
                            f"Stock insuficiente para '{prod.nombre}' al confirmar. "
                            f"Disponible: {prod.stock_cantidad}, requerido: {detalle.cantidad}."
                        )
                    prod.stock_cantidad -= detalle.cantidad
                    uow.productos.add(prod)
                else:
                    # MANUFACTURADO: descontar ingredientes (respetando personalización)
                    pi_list = uow.productos.get_producto_ingredientes(prod.id)
                    personalizacion = detalle.personalizacion or []
                    for pi in pi_list:
                        if pi.ingrediente_id in personalizacion:
                            continue  # saltear removidos
                        ingrediente = uow.ingredientes.get_by_id_for_update(pi.ingrediente_id)
                        if not ingrediente:
                            continue
                        necesario = pi.cantidad * detalle.cantidad
                        if ingrediente.stock_cantidad < necesario:
                            raise ConflictError(
                                f"Stock insuficiente de '{ingrediente.nombre}' "
                                f"al confirmar '{prod.nombre}'."
                            )
                        ingrediente.stock_cantidad -= necesario
                        uow.ingredientes.add(ingrediente)

            pedido.estado_codigo = "CONFIRMADO"
            pedido.updated_at    = datetime.now(timezone.utc)
            uow.pedidos.add(pedido)

            # Historial: usuario_id=None (acción de sistema, no humano)
            uow.historial.add(HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_desde=estado_actual,
                estado_hacia="CONFIRMADO",
                usuario_id=None,
                motivo=motivo,
            ))

            result = self._build_public(uow, pedido)
        return result

    # ── Soft delete ───────────────────────────────────────────────────────────

    def soft_delete(self, pedido_id: int) -> None:
        with PedidoUnitOfWork(self._session) as uow:
            pedido = self._get_or_404(uow, pedido_id)
            if pedido.estado_codigo == "ENTREGADO":
                raise ConflictError("No se puede eliminar un pedido ya entregado.")

            # Si el pedido ya había decrementado stock, restaurarlo 
            if pedido.estado_codigo in _ESTADOS_STOCK_DECREMENTADO:
                detalles = uow.pedidos.get_detalles(pedido.id)
                for detalle in detalles:
                    prod = uow.productos.get_by_id_for_update(detalle.producto_id)
                    if not prod:
                        continue

                    if prod.tipo == TipoProducto.TERMINADO:
                        prod.stock_cantidad += detalle.cantidad
                        uow.productos.add(prod)
                    else:
                        pi_list = uow.productos.get_producto_ingredientes(prod.id)
                        personalizacion = detalle.personalizacion or []
                        for pi in pi_list:
                            if pi.ingrediente_id in personalizacion:
                                continue
                            ingrediente = uow.ingredientes.get_by_id_for_update(pi.ingrediente_id)
                            if not ingrediente:
                                continue
                            necesario = pi.cantidad * detalle.cantidad
                            ingrediente.stock_cantidad += necesario
                            uow.ingredientes.add(ingrediente)

            pedido.deleted_at = datetime.now(timezone.utc)
            pedido.updated_at = datetime.now(timezone.utc)
            uow.pedidos.add(pedido)

    # ── Historial ─────────────────────────────────────────────────────────────

    def get_historial(self, pedido_id: int) -> list[HistorialPublic]:
        with PedidoUnitOfWork(self._session) as uow:
            self._get_or_404(uow, pedido_id)
        return HistorialService(self._session).get_by_pedido(pedido_id)
