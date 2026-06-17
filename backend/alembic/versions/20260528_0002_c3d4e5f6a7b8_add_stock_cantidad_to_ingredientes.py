"""add_stock_cantidad_to_ingredientes

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-28 00:02:00.000000

Agrega la columna stock_cantidad a la tabla ingredientes.
- NUMERIC(10,3): permite decimales como 0.500 kg.
- NOT NULL DEFAULT 0: sin romper filas existentes.
- CHECK stock_cantidad >= 0: integridad de dominio (D1).
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ADD COLUMN con server_default para no romper filas existentes
    op.add_column(
        "ingredientes",
        sa.Column(
            "stock_cantidad",
            sa.Numeric(precision=10, scale=3),
            nullable=False,
            server_default="0",
        ),
    )
    # CHECK constraint: stock_cantidad >= 0
    op.create_check_constraint(
        "ck_ingredientes_stock_nn",
        "ingredientes",
        "stock_cantidad >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_ingredientes_stock_nn", "ingredientes", type_="check")
    op.drop_column("ingredientes", "stock_cantidad")
