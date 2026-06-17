# app/modules/productos/service.py
"""
Service del módulo productos.

Responsabilidades:
  - CRUD de Producto con validaciones MANUFACTURADO/TERMINADO.
  - Cálculo on-the-fly de precio_costo. Nunca persistido.
  - Endpoint aplicar_margen: actualiza precio_base de productos MANUFACTURADOS
    basándose en precio_costo × (1 + margen/100).
  - Gestión de disponibilidad y stock.
  - Borrado lógico y reactivación.

Aritmética con Decimal para evitar errores de punto flotante.
"""
from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Session

from app.core.codigo import generar_codigo
from app.core.exceptions.custom_exceptions import (
    ConflictError,
    DuplicateResourceError,
    ResourceNotFoundError,
    ValidationError,
)
from app.modules.productos.models import (
    Producto,
    ProductoCategoria,
    ProductoIngrediente,
    TipoProducto,
)
from app.modules.productos.schemas import (
    AplicarMargenRequest,
    AplicarMargenResponse,
    AplicarMargenScope,
    CategoriaEnProducto,
    DisponibilidadUpdate,
    IngredienteEnProducto,
    ProductoCreate,
    ProductoIgnorado,
    ProductoList,
    ProductoMargenResult,
    ProductoPublic,
    ProductoUpdate,
    StockUpdate,
)
from app.modules.productos.unit_of_work import ProductoUnitOfWork

_QUANT = Decimal("0.01")  # cuantización para campos monetarios (2 decimales)


def _q(value: Decimal) -> Decimal:
    """Redondea un Decimal a 2 decimales (ROUND_HALF_EVEN = banker's rounding)."""
    return value.quantize(_QUANT)


class ProductoService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ─────────────────────────────────────────────────────

    def _get_or_404(self, uow: ProductoUnitOfWork, producto_id: int) -> Producto:
        prod = uow.productos.get_by_id(producto_id)
        if not prod:
            raise ResourceNotFoundError(f"Producto con id={producto_id} no encontrado.")
        return prod

    def _calcular_precio_costo(
        self,
        uow: ProductoUnitOfWork,
        producto_id: int,
        tipo: TipoProducto,
    ) -> Decimal:
        """
        Calcula el costo de producción de un producto MANUFACTURADO sumando
        cantidad × costo_unitario para cada ingrediente. 
        Los TERMINADOS siempre devuelven 0.
        """
        if tipo == TipoProducto.TERMINADO:
            return Decimal("0.00")
        links = uow.productos.get_producto_ingredientes(producto_id)
        total = Decimal("0.0000")
        for pi in links:
            ing = uow.ingredientes.get_by_id(pi.ingrediente_id)
            if ing:
                total += pi.cantidad * ing.costo
        return _q(total)

    def _build_public(self, uow: ProductoUnitOfWork, prod: Producto) -> ProductoPublic:
        """Construye ProductoPublic enriquecido con categorías, ingredientes y precio_costo."""
        # Categorías
        cat_links = uow.productos.get_producto_categorias(prod.id)
        categorias_out = []
        for cl in cat_links:
            cat = uow.categorias.get_by_id(cl.categoria_id)
            if cat:
                categorias_out.append(CategoriaEnProducto(
                    id=cat.id,
                    nombre=cat.nombre,
                    es_principal=cl.es_principal,
                ))

        # Ingredientes con subtotal_costo
        ing_links = uow.productos.get_producto_ingredientes(prod.id)
        ingredientes_out = []
        for pi in ing_links:
            ing = uow.ingredientes.get_by_id(pi.ingrediente_id)
            if ing:
                subtotal = _q(pi.cantidad * ing.costo)
                ingredientes_out.append(IngredienteEnProducto(
                    id=ing.id,
                    nombre=ing.nombre,
                    es_alergeno=ing.es_alergeno,
                    es_removible=pi.es_removible,
                    es_opcional=pi.es_opcional,
                    cantidad=pi.cantidad,
                    unidad_medida=ing.unidad_medida,
                    costo_unitario=ing.costo,
                    subtotal_costo=subtotal,
                ))

            # Stock efectivo: TERMINADO usa su stock propio; MANUFACTURADO se deriva
        # del stock de ingredientes (cuántas unidades se pueden producir hoy).
        if prod.tipo == TipoProducto.MANUFACTURADO and ing_links:
            producibles = []
            for pi in ing_links:
                ing = uow.ingredientes.get_by_id(pi.ingrediente_id)
                if ing and pi.cantidad > 0:
                    producibles.append(int(ing.stock_cantidad // pi.cantidad))
            stock_efectivo = min(producibles) if producibles else 0
        else:
            stock_efectivo = prod.stock_cantidad

        precio_costo = self._calcular_precio_costo(uow, prod.id, prod.tipo)

        return ProductoPublic(
            id=prod.id,
            codigo=prod.codigo,
            nombre=prod.nombre,
            descripcion=prod.descripcion,
            imagenes_url=prod.imagenes_url,
            tiempo_prep_min=prod.tiempo_prep_min,
            tipo=prod.tipo,
            precio_base=prod.precio_base,
            precio_costo=precio_costo,
            stock_cantidad=stock_efectivo,
            disponible=prod.disponible,
            unidad_venta_id=prod.unidad_venta_id,
            activo=prod.activo,
            categorias=categorias_out,
            ingredientes=ingredientes_out,
            created_at=prod.created_at,
            updated_at=prod.updated_at,
        )

    def _validar_ingredientes_manufacturado(self, data: ProductoCreate | ProductoUpdate) -> None:
        """
        Valida reglas de negocio para productos MANUFACTURADOS.
        Solo se llama cuando tipo == MANUFACTURADO.
        """
        if not data.ingredientes:
            raise ValidationError("Debe cargar un ingrediente para guardarlo")
        for ing_input in data.ingredientes:
            if ing_input.cantidad <= 0:
                raise ValidationError("Cada ingrediente debe tener cantidad mayor a 0")

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def create(self, data: ProductoCreate) -> ProductoPublic:
        if data.tipo == TipoProducto.MANUFACTURADO:
            self._validar_ingredientes_manufacturado(data)

        with ProductoUnitOfWork(self._session) as uow:
            # Validar nombre único
            if uow.productos.get_by_nombre_exacto(data.nombre):
                raise DuplicateResourceError(f"Ya existe un producto con nombre '{data.nombre}'.")

            codigo = generar_codigo(self._session, "producto")
            prod = Producto(
                codigo=codigo,
                nombre=data.nombre,
                descripcion=data.descripcion,
                imagenes_url=data.imagenes_url,
                tiempo_prep_min=data.tiempo_prep_min,
                tipo=data.tipo,
                precio_base=data.precio_base,
                stock_cantidad=data.stock_cantidad,
                disponible=data.disponible,
                unidad_venta_id=data.unidad_venta_id,
            )
            uow.productos.add(prod)

            # Categorías
            for i, cat_id in enumerate(data.categoria_ids):
                cat = uow.categorias.get_by_id(cat_id)
                if not cat:
                    raise ResourceNotFoundError(f"Categoría id={cat_id} no encontrada.")
                uow.productos.add_link(ProductoCategoria(
                    producto_id=prod.id,
                    categoria_id=cat_id,
                    es_principal=(i == 0),
                ))

            # Ingredientes
            for ing_input in data.ingredientes:
                ing = uow.ingredientes.get_by_id(ing_input.ingrediente_id)
                if not ing:
                    raise ResourceNotFoundError(
                        f"Ingrediente id={ing_input.ingrediente_id} no encontrado."
                    )
                uow.productos.add_link(ProductoIngrediente(
                    producto_id=prod.id,
                    ingrediente_id=ing_input.ingrediente_id,
                    cantidad=ing_input.cantidad,
                    # ERD: la unidad de la receta = unidad base del ingrediente
                    unidad_medida_id=ing.unidad_medida_id,
                    es_removible=ing_input.es_removible,
                    es_opcional=ing_input.es_opcional,
                ))

            result = self._build_public(uow, prod)
        return result

    def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        incluir_inactivos: bool = False,
        nombre: str | None = None,
        categoria_id: int | None = None,
        sort_by: str = "nombre",
        sort_dir: str = "asc",
    ) -> ProductoList:
        with ProductoUnitOfWork(self._session) as uow:
            productos = uow.productos.get_all_activos(
                offset=offset, limit=limit,
                incluir_inactivos=incluir_inactivos, nombre=nombre,
                categoria_id=categoria_id,
                sort_by=sort_by, sort_dir=sort_dir,
            )
            total = uow.productos.count_activos(
                incluir_inactivos=incluir_inactivos, nombre=nombre,
                categoria_id=categoria_id,
            )
            result = ProductoList(
                data=[self._build_public(uow, p) for p in productos],
                total=total,
            )
        return result

    def get_by_id(self, producto_id: int) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            prod = self._get_or_404(uow, producto_id)
            result = self._build_public(uow, prod)
        return result

    def update(self, producto_id: int, data: ProductoUpdate) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            prod = self._get_or_404(uow, producto_id)
            if prod.deleted_at is not None:
                raise ConflictError("No se puede editar un producto desactivado.")

            # Tipo EFECTIVO tras el PATCH (data.tipo si vino, si no el actual del producto).
            tipo_efectivo = data.tipo if data.tipo is not None else prod.tipo
            if tipo_efectivo == TipoProducto.MANUFACTURADO:
                if data.ingredientes is not None:
                    self._validar_ingredientes_manufacturado(data)
                elif not uow.productos.get_producto_ingredientes(prod.id):
                    raise ValidationError("Debe cargar un ingrediente para guardarlo")

            if data.nombre is not None and data.nombre != prod.nombre:
                otro = uow.productos.get_by_nombre_exacto(data.nombre)
                if otro and otro.id != producto_id:
                    raise DuplicateResourceError(
                        f"Ya existe otro producto con nombre '{data.nombre}'."
                    )

            for field, value in data.model_dump(
                exclude_unset=True, exclude={"categoria_ids", "ingredientes"}
            ).items():
                setattr(prod, field, value)
            prod.updated_at = datetime.now(timezone.utc)
            uow.productos.add(prod)

            if data.categoria_ids is not None:
                uow.productos.delete_categorias(prod.id)
                for i, cat_id in enumerate(data.categoria_ids):
                    cat = uow.categorias.get_by_id(cat_id)
                    if not cat:
                        raise ResourceNotFoundError(f"Categoría id={cat_id} no encontrada.")
                    uow.productos.add_link(ProductoCategoria(
                        producto_id=prod.id, categoria_id=cat_id, es_principal=(i == 0)
                    ))

            if data.ingredientes is not None:
                uow.productos.delete_ingredientes(prod.id)
                for ing_input in data.ingredientes:
                    ing = uow.ingredientes.get_by_id(ing_input.ingrediente_id)
                    if not ing:
                        raise ResourceNotFoundError(
                            f"Ingrediente id={ing_input.ingrediente_id} no encontrado."
                        )
                    uow.productos.add_link(ProductoIngrediente(
                        producto_id=prod.id,
                        ingrediente_id=ing_input.ingrediente_id,
                        cantidad=ing_input.cantidad,
                        unidad_medida_id=ing.unidad_medida_id,
                        es_removible=ing_input.es_removible,
                        es_opcional=ing_input.es_opcional,
                    ))

            result = self._build_public(uow, prod)
        return result

    def desactivar(self, producto_id: int) -> None:
        with ProductoUnitOfWork(self._session) as uow:
            prod = self._get_or_404(uow, producto_id)
            if prod.deleted_at is not None:
                raise ConflictError("El producto ya está desactivado.")
            prod.deleted_at = datetime.now(timezone.utc)
            prod.updated_at = datetime.now(timezone.utc)
            uow.productos.add(prod)

    def reactivar(self, producto_id: int) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            prod = self._get_or_404(uow, producto_id)
            if prod.deleted_at is None:
                raise ConflictError("El producto ya está activo.")
            prod.deleted_at = None
            prod.updated_at = datetime.now(timezone.utc)
            uow.productos.add(prod)
            result = self._build_public(uow, prod)
        return result

    def actualizar_disponibilidad(
        self, producto_id: int, data: DisponibilidadUpdate
    ) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            prod = self._get_or_404(uow, producto_id)
            prod.disponible = data.disponible
            prod.updated_at = datetime.now(timezone.utc)
            uow.productos.add(prod)
            result = self._build_public(uow, prod)
        return result

    def actualizar_stock(self, producto_id: int, data: StockUpdate) -> ProductoPublic:
        with ProductoUnitOfWork(self._session) as uow:
            prod = self._get_or_404(uow, producto_id)
            prod.stock_cantidad = data.stock_cantidad
            prod.updated_at = datetime.now(timezone.utc)
            uow.productos.add(prod)
            result = self._build_public(uow, prod)
        return result

    # ── Aplicar margen masivo  ──────────────────────────────

    def aplicar_margen(self, data: AplicarMargenRequest) -> AplicarMargenResponse:
        """
        Recalcula precio_base de productos MANUFACTURADOS usando:
            precio_nuevo = precio_costo × (1 + margen/100)
        Los TERMINADOS se ignoran silenciosamente .
        El scope=categoria incluye productos de los descendientes .
        """
        factor = Decimal("1") + data.margen_porcentaje / Decimal("100")

        with ProductoUnitOfWork(self._session) as uow:
            # 1. Resolver lista de productos según scope
            if data.scope == AplicarMargenScope.PRODUCTOS:
                productos = [
                    uow.productos.get_by_id(pid)
                    for pid in (data.producto_ids or [])
                ]
                productos = [p for p in productos if p and p.deleted_at is None]
            else:
                cat_ids = uow.categorias.get_descendientes_ids(data.categoria_id)
                productos = uow.productos.get_by_categoria_ids(cat_ids)

            actualizados: list[ProductoMargenResult] = []
            ignorados: list[ProductoIgnorado] = []

            for prod in productos:
                # 2. Ignorar TERMINADOS (RN-PR08)
                if prod.tipo == TipoProducto.TERMINADO:
                    ignorados.append(ProductoIgnorado(
                        producto_id=prod.id,
                        razon="Producto TERMINADO (no aplica margen automático)",
                    ))
                    continue

                # 3. Calcular precio_costo y precio_nuevo
                precio_costo  = self._calcular_precio_costo(uow, prod.id, prod.tipo)
                precio_nuevo  = _q(precio_costo * factor)
                precio_anterior = prod.precio_base

                # 4. Actualizar
                prod.precio_base = precio_nuevo
                prod.updated_at  = datetime.now(timezone.utc)
                uow.productos.add(prod)

                actualizados.append(ProductoMargenResult(
                    producto_id=prod.id,
                    nombre=prod.nombre,
                    precio_anterior=precio_anterior,
                    precio_costo=precio_costo,
                    precio_nuevo=precio_nuevo,
                ))

        return AplicarMargenResponse(actualizados=actualizados, ignorados=ignorados)
