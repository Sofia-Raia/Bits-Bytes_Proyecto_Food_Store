from typing import Optional
# app/modules/categorias/service.py
from datetime import datetime, timezone

from sqlmodel import Session

from app.core.codigo import generar_codigo
from app.core.exceptions.custom_exceptions import (
    BusinessRuleError,
    ConflictError,
    DuplicateResourceError,
    ResourceNotFoundError,
)
from app.modules.categorias.models import Categoria
from app.modules.categorias.schemas import (
    CategoriaCreate, CategoriaPublic, CategoriaUpdate,
    CategoriaList, CategoriaTree, CategoriaTreeList,
)
from app.modules.categorias.unit_of_work import CategoriaUnitOfWork


class CategoriaService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_or_404(self, uow: CategoriaUnitOfWork, categoria_id: int) -> Categoria:
        cat = uow.categorias.get_by_id(categoria_id)
        if not cat:
            raise ResourceNotFoundError(f"Categoría con id={categoria_id} no encontrada")
        return cat

    def _assert_nombre_unico(self, uow: CategoriaUnitOfWork, nombre: str) -> None:
        existing = uow.categorias.get_by_nombre(nombre)
        if existing and existing.activo:
            raise DuplicateResourceError(f"Ya existe una categoría activa con el nombre '{nombre}'")

    def _validar_parent(self, uow: CategoriaUnitOfWork, parent_id: int) -> None:
        parent = uow.categorias.get_by_id(parent_id)
        if not parent or not parent.activo:
            raise ResourceNotFoundError(
                f"Categoría padre con id={parent_id} no encontrada o inactiva"
            )

    def _detectar_ciclo(
        self, uow: CategoriaUnitOfWork, categoria_id: int, nuevo_parent_id: int
    ) -> None:
        visitados: set[int] = set()
        cursor = nuevo_parent_id
        while cursor is not None:
            if cursor == categoria_id:
                raise BusinessRuleError("La operación crearía un ciclo en el árbol de categorías.")
            if cursor in visitados:
                break
            visitados.add(cursor)
            nodo = uow.categorias.get_by_id(cursor)
            if not nodo:
                break
            cursor = nodo.parent_id

    def _categoria_to_tree(
        self, cat: Categoria, incluir_inactivos: bool = False
    ) -> CategoriaTree:
        return CategoriaTree(
            id=cat.id,
            codigo=cat.codigo,
            nombre=cat.nombre,
            descripcion=cat.descripcion,
            imagen_url=cat.imagen_url,
            parent_id=cat.parent_id,
            activo=cat.activo,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
            subcategorias=[
                self._categoria_to_tree(hijo, incluir_inactivos)
                for hijo in cat.subcategorias
                if incluir_inactivos or hijo.activo
            ],
        )

    # ── Casos de uso ──────────────────────────────────────────────────────────

    def create(self, data: CategoriaCreate) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            self._assert_nombre_unico(uow, data.nombre)
            if data.parent_id is not None:
                self._validar_parent(uow, data.parent_id)
            codigo = generar_codigo(self._session, "categoria")
            cat = Categoria(
                codigo=codigo,
                nombre=data.nombre,
                descripcion=data.descripcion,
                imagen_url=data.imagen_url,
                parent_id=data.parent_id,
            )
            uow.categorias.add(cat)
            result = CategoriaPublic.model_validate(cat)
        return result

    def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        incluir_inactivos: bool = False,
        nombre: Optional[str] = None,
    ) -> CategoriaList:
        with CategoriaUnitOfWork(self._session) as uow:
            cats = uow.categorias.get_all_activas(
                offset=offset, limit=limit,
                incluir_inactivos=incluir_inactivos, nombre=nombre,
            )
            total = uow.categorias.count_activas(incluir_inactivos=incluir_inactivos, nombre=nombre)
            result = CategoriaList(
                data=[CategoriaPublic.model_validate(c) for c in cats],
                total=total,
            )
        return result

    def get_by_id(self, categoria_id: int) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            cat = self._get_or_404(uow, categoria_id)
            result = CategoriaPublic.model_validate(cat)
        return result

    def update(self, categoria_id: int, data: CategoriaUpdate) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            cat = self._get_or_404(uow, categoria_id)
            if not cat.activo:
                raise ConflictError("No se puede editar una categoría inactiva. Reactivala primero.")
            if data.nombre and data.nombre != cat.nombre:
                self._assert_nombre_unico(uow, data.nombre)
            if data.parent_id is not None and data.parent_id != cat.parent_id:
                if data.parent_id == categoria_id:
                    raise BusinessRuleError("Una categoría no puede ser su propio padre")
                self._validar_parent(uow, data.parent_id)
                self._detectar_ciclo(uow, categoria_id, data.parent_id)
            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(cat, field, value)
            cat.updated_at = datetime.now(timezone.utc)
            uow.categorias.add(cat)
            result = CategoriaPublic.model_validate(cat)
        return result

    def desactivar(self, categoria_id: int) -> None:
        with CategoriaUnitOfWork(self._session) as uow:
            cat = self._get_or_404(uow, categoria_id)
            if not cat.activo:
                raise ConflictError("La categoría ya está inactiva")

            hijos_activos = uow.categorias.get_children(categoria_id)
            if hijos_activos:
                raise ConflictError(
                    f"No se puede desactivar '{cat.nombre}': tiene "
                    f"{len(hijos_activos)} subcategoría(s) activa(s). Desactiválas primero."
                )

            # RN-CA03: tampoco si tiene productos activos asociados
            productos_activos = uow.categorias.count_productos_activos(categoria_id)
            if productos_activos > 0:
                raise ConflictError(
                    f"No se puede desactivar '{cat.nombre}': tiene "
                    f"{productos_activos} producto(s) activo(s) asociado(s). "
                    "Desasociálos o desactiválos primero."
                )

            cat.deleted_at = datetime.now(timezone.utc)
            cat.updated_at = datetime.now(timezone.utc)
            uow.categorias.add(cat)

    def reactivar(self, categoria_id: int) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            cat = self._get_or_404(uow, categoria_id)
            if cat.activo:
                raise ConflictError("La categoría ya está activa")
            if cat.parent_id is not None:
                parent = uow.categorias.get_by_id(cat.parent_id)
                if not parent or not parent.activo:
                    raise ConflictError(
                        "No se puede reactivar: la categoría padre está inactiva. Reactivala primero."
                    )
            cat.deleted_at = None
            cat.updated_at = datetime.now(timezone.utc)
            uow.categorias.add(cat)
            result = CategoriaPublic.model_validate(cat)
        return result

    def get_tree(self, incluir_inactivos: bool = False) -> CategoriaTreeList:
        with CategoriaUnitOfWork(self._session) as uow:
            roots = uow.categorias.get_roots(incluir_inactivos=incluir_inactivos)
            total = uow.categorias.count_roots(incluir_inactivos=incluir_inactivos)
            result = CategoriaTreeList(
                data=[self._categoria_to_tree(r, incluir_inactivos) for r in roots],
                total=total,
            )
        return result

    def get_subcategorias(self, categoria_id: int) -> CategoriaList:
        with CategoriaUnitOfWork(self._session) as uow:
            self._get_or_404(uow, categoria_id)
            hijos = uow.categorias.get_children(categoria_id)
            result = CategoriaList(
                data=[CategoriaPublic.model_validate(h) for h in hijos],
                total=len(hijos),
            )
        return result
