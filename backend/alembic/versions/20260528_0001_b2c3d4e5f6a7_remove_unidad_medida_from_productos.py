"""remove_unidad_medida_from_productos

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-28 00:01:00.000000

Elimina la columna unidad_medida de la tabla productos.

Notas:
  - El tipo ENUM 'unidadmedida' NO se elimina: sigue siendo usado por
    la columna ingredientes.unidad_medida.
  - El downgrade agrega la columna con server_default='UNIDADES' para
    que las filas existentes reciban un valor válido y no violen NOT NULL.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # DROP COLUMN — simple, sin tocar el tipo enum (lo sigue usando ingredientes)
    op.drop_column("productos", "unidad_medida")


def downgrade() -> None:
    # Restaura la columna con un default temporal para no violar NOT NULL en filas existentes
    op.add_column(
        "productos",
        sa.Column(
            "unidad_medida",
            sa.Enum("KG", "L", "UNIDADES", name="unidadmedida"),
            nullable=False,
            server_default="UNIDADES",
        ),
    )
    # Una vez agregada la columna, removemos el server_default para mantener
    # la columna sin default explícito (igual que el estado original)
    op.alter_column("productos", "unidad_medida", server_default=None)
