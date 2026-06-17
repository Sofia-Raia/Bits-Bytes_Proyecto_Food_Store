"""unique partial soft delete

Revision ID: a1b2c3d4e5f6
Revises: 0e442c6c21db
Create Date: 2026-05-24 22:00:00.000000+00:00

Convierte los índices únicos totales en (email, nombre) de tablas con soft-delete
en índices únicos parciales (WHERE deleted_at IS NULL), de modo que un
registro soft-deleteado no impida la creación de otro con el mismo valor.

La migración inicial creó estas columnas como CREATE INDEX UNIQUE (ix_*),
no como UNIQUE CONSTRAINT, por eso se usa drop_index en lugar de drop_constraint.

Se usa op.execute() con SQL raw para el CREATE UNIQUE INDEX parcial porque
op.inline_literal() entrecomilla la expresión WHERE y PostgreSQL la rechaza
como tipo boolean.

Tablas afectadas:
  - usuarios.email
  - categorias.nombre
  - productos.nombre
  - ingredientes.nombre

Las columnas `codigo` quedan como índice único total (son inmutables y no se reusan).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "0e442c6c21db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (tabla, columna, indice_actual, indice_parcial_nuevo)
# indice_actual: nombre generado por op.f() en la migración inicial → ix_tabla_columna
_TARGETS = [
    ("usuarios",     "email",  "ix_usuarios_email",      "ux_usuarios_email_activos"),
    ("categorias",   "nombre", "ix_categorias_nombre",   "ux_categorias_nombre_activos"),
    ("productos",    "nombre", "ix_productos_nombre",    "ux_productos_nombre_activos"),
    ("ingredientes", "nombre", "ix_ingredientes_nombre", "ux_ingredientes_nombre_activos"),
]


def upgrade() -> None:
    for tabla, columna, indice_actual, indice_parcial in _TARGETS:
        # Drop del índice único total creado por la migración inicial.
        op.drop_index(indice_actual, table_name=tabla)
        # Índice único parcial via SQL raw: op.inline_literal() entrecomilla
        # la expresión y PostgreSQL la rechaza como boolean. Con op.execute()
        # el WHERE se interpreta correctamente como expresión SQL.
        op.execute(
            f"CREATE UNIQUE INDEX {indice_parcial} ON {tabla} ({columna}) WHERE deleted_at IS NULL"
        )


def downgrade() -> None:
    for tabla, columna, indice_actual, indice_parcial in _TARGETS:
        op.execute(f"DROP INDEX IF EXISTS {indice_parcial}")
        # Restaura el índice único total original.
        op.create_index(indice_actual, tabla, [columna], unique=True)