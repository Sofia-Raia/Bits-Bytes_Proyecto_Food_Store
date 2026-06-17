# app/modules/ingredientes/service.py
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlmodel import Session

from app.core.codigo import generar_codigo
from app.core.exceptions.custom_exceptions import (
    ConflictError,
    DuplicateResourceError,
    ResourceNotFoundError,
)
from app.modules.ingredientes.models import Ingrediente
from app.modules.ingredientes.schemas import (
    IngredienteCreate, IngredientePublic, IngredienteUpdate, IngredienteList,
    StockIngredienteUpdate, UnidadMedidaPublic,
)
from app.modules.ingredientes.unit_of_work import IngredienteUnitOfWork


class IngredienteService:

    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: IngredienteUnitOfWork, ingrediente_id: int) -> Ingrediente:
        ing = uow.ingredientes.get_by_id(ingrediente_id)
        if not ing:
            raise ResourceNotFoundError(f"Ingrediente con id={ingrediente_id} no encontrado")
        return ing

    def _assert_nombre_unico(self, uow: IngredienteUnitOfWork, nombre: str) -> None:
        existing = uow.ingredientes.get_by_nombre(nombre)
        if existing and existing.activo:
            raise DuplicateResourceError(f"Ya existe un ingrediente activo con el nombre '{nombre}'")

    def _resolver_unidad_id(self, uow: IngredienteUnitOfWork, codigo: str) -> int:
        """Traduce el código de unidad (KG, L, ...) al id del catálogo UnidadMedida."""
        unidad = uow.ingredientes.get_unidad_by_codigo(codigo)
        if not unidad:
            raise ConflictError(
                f"Unidad de medida '{codigo}' no existe en el catálogo. "
                f"Consultá GET /api/v1/ingredientes/unidades-medida."
            )
        return unidad.id

    def listar_unidades(self) -> list[UnidadMedidaPublic]:
        """Catálogo de unidades de medida (solo-lectura)."""
        with IngredienteUnitOfWork(self._session) as uow:
            return [UnidadMedidaPublic.model_validate(u) for u in uow.ingredientes.list_unidades()]

    def create(self, data: IngredienteCreate) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            self._assert_nombre_unico(uow, data.nombre)
            unidad_id = self._resolver_unidad_id(uow, data.unidad_medida)
            codigo = generar_codigo(self._session, "ingrediente")
            ing = Ingrediente(
                codigo=codigo,
                nombre=data.nombre,
                descripcion=data.descripcion,
                es_alergeno=data.es_alergeno,
                costo=data.costo,
                unidad_medida_id=unidad_id,
                stock_cantidad=data.stock_cantidad,
            )
            uow.ingredientes.add(ing)
            result = IngredientePublic.model_validate(ing)
        return result

    def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        incluir_inactivos: bool = False,
        nombre: Optional[str] = None,
        sort_by: str = 'nombre',
        sort_dir: str = 'asc',
    ) -> IngredienteList:
        with IngredienteUnitOfWork(self._session) as uow:
            ings = uow.ingredientes.get_all_paginado(
                offset=offset, limit=limit,
                incluir_inactivos=incluir_inactivos, nombre=nombre,
                sort_by=sort_by, sort_dir=sort_dir,
            )
            total = uow.ingredientes.count(
                incluir_inactivos=incluir_inactivos, nombre=nombre,
            )
            result = IngredienteList(
                data=[IngredientePublic.model_validate(i) for i in ings],
                total=total,
            )
        return result

    def get_by_id(self, ingrediente_id: int) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            ing = self._get_or_404(uow, ingrediente_id)
            result = IngredientePublic.model_validate(ing)
        return result

    def update(self, ingrediente_id: int, data: IngredienteUpdate) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            ing = self._get_or_404(uow, ingrediente_id)
            if not ing.activo:
                raise ConflictError("No se puede editar un ingrediente inactivo. Reactivalo primero.")
            if data.nombre and data.nombre != ing.nombre:
                self._assert_nombre_unico(uow, data.nombre)
            patch = data.model_dump(exclude_unset=True)
            # 'unidad_medida' llega como código → resolver a unidad_medida_id (es property RO)
            if "unidad_medida" in patch:
                codigo = patch.pop("unidad_medida")
                if codigo is not None:
                    ing.unidad_medida_id = self._resolver_unidad_id(uow, codigo)
            for field, value in patch.items():
                setattr(ing, field, value)
            ing.updated_at = datetime.now(timezone.utc)
            uow.ingredientes.add(ing)
            result = IngredientePublic.model_validate(ing)
        return result

    def desactivar(self, ingrediente_id: int) -> None:
        with IngredienteUnitOfWork(self._session) as uow:
            ing = self._get_or_404(uow, ingrediente_id)
            if not ing.activo:
                raise ConflictError("El ingrediente ya está inactivo")
            ing.deleted_at = datetime.now(timezone.utc)
            ing.updated_at = datetime.now(timezone.utc)
            uow.ingredientes.add(ing)

    def reactivar(self, ingrediente_id: int) -> IngredientePublic:
        with IngredienteUnitOfWork(self._session) as uow:
            ing = self._get_or_404(uow, ingrediente_id)
            if ing.activo:
                raise ConflictError("El ingrediente ya está activo")
            ing.deleted_at = None
            ing.updated_at = datetime.now(timezone.utc)
            uow.ingredientes.add(ing)
            result = IngredientePublic.model_validate(ing)
        return result

    def actualizar_stock(self, ingrediente_id: int, stock_cantidad: Decimal) -> IngredientePublic:
        """
        Setea el stock del ingrediente al valor absoluto indicado (D4).
        Acepta cualquier valor >= 0 (reposición o ajuste por merma).
        """
        with IngredienteUnitOfWork(self._session) as uow:
            ing = self._get_or_404(uow, ingrediente_id)
            if not ing.activo:
                raise ConflictError("No se puede actualizar stock de un ingrediente inactivo.")
            ing.stock_cantidad = stock_cantidad
            ing.updated_at = datetime.now(timezone.utc)
            uow.ingredientes.add(ing)
            result = IngredientePublic.model_validate(ing)
        return result
