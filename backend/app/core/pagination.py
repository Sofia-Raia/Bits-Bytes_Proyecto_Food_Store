# app/core/pagination.py
"""
Envoltura de paginación estándar de la API (convención global, sección 5 del spec).

Todas las colecciones paginadas se serializan como:

    { "items": [...], "total": N, "page": 1, "size": 20, "pages": P }

Donde:
- items: página actual de resultados.
- total: cantidad total de registros que matchean el filtro (sin paginar).
- page:  número de página solicitado (1-based).
- size:  tamaño de página solicitado.
- pages: cantidad total de páginas = ceil(total / size).

`page` y `size` se aceptan como query params en los endpoints de listado y se
traducen internamente a offset/limit para los servicios y repositorios, que
permanecen sin cambios.
"""
from math import ceil
from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int


def offset_de(page: int, size: int) -> int:
    """Convierte (page, size) en el offset que esperan los repositorios."""
    return (page - 1) * size


def paginar(items: List[T], total: int, page: int, size: int) -> "Paginated[T]":
    """Construye la respuesta paginada calculando la cantidad de páginas."""
    pages = ceil(total / size) if size > 0 else 0
    return Paginated(items=items, total=total, page=page, size=size, pages=pages)
