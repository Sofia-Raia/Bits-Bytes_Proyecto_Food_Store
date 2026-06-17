# app/core/types.py
"""
Tipos compartidos para campos monetarios y de cantidad.

Usamos Decimal en la capa de modelo/BD (Numeric en PostgreSQL) para evitar
errores de punto flotante en precios y costos.

Para la serialización JSON (respuestas de la API), anotamos con PlainSerializer
para que Pydantic v2 emita `float` en lugar de `str`, que es el default para Decimal.

Uso:
    from app.core.types import MoneyDecimal, QuantityDecimal

    class MiSchema(SQLModel):
        precio: MoneyDecimal
        cantidad: QuantityDecimal
"""

from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

# Campo monetario: 2 decimales en DB (Numeric 12,2), float en JSON
MoneyDecimal = Annotated[
    Decimal,
    PlainSerializer(lambda x: float(x), return_type=float, when_used="json"),
]

# Campo de cantidad (ingrediente por unidad de producto): 4 decimales en DB
# Permite expresar "0.250 kg" con precisión sin errores de float.
QuantityDecimal = Annotated[
    Decimal,
    PlainSerializer(lambda x: float(x), return_type=float, when_used="json"),
]
