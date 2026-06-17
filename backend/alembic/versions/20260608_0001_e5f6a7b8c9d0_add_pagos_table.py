"""add_pagos_table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-08 00:00:00.000000

Parte 4 — MercadoPago.
Crea la tabla `pagos` para registrar los intentos de pago vía MercadoPago.
- monto en NUMERIC(12,2) (Decimal, nunca float).
- estado interno propio: pendiente | aprobado | rechazado.
- campos mp_* con la info que devuelve MercadoPago (preferencia, pago, merchant order).
- idempotency_key UNIQUE para no reprocesar el mismo intento.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pagos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="pendiente"),
        sa.Column("mp_preference_id", sa.String(length=120), nullable=True),
        sa.Column("mp_init_point", sa.String(length=500), nullable=True),
        sa.Column("mp_payment_id", sa.BigInteger(), nullable=True),
        sa.Column("mp_merchant_order_id", sa.BigInteger(), nullable=True),
        sa.Column("mp_status", sa.String(length=40), nullable=True),
        sa.Column("mp_status_detail", sa.String(length=120), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_pagos_idempotency_key"),
    )
    op.create_index("ix_pagos_pedido_id", "pagos", ["pedido_id"])
    op.create_index("ix_pagos_estado", "pagos", ["estado"])
    op.create_index("ix_pagos_mp_payment_id", "pagos", ["mp_payment_id"])
    op.create_index("ix_pagos_mp_merchant_order_id", "pagos", ["mp_merchant_order_id"])
    op.create_index("ix_pagos_idempotency_key", "pagos", ["idempotency_key"])


def downgrade() -> None:
    op.drop_index("ix_pagos_idempotency_key", table_name="pagos")
    op.drop_index("ix_pagos_mp_merchant_order_id", table_name="pagos")
    op.drop_index("ix_pagos_mp_payment_id", table_name="pagos")
    op.drop_index("ix_pagos_estado", table_name="pagos")
    op.drop_index("ix_pagos_pedido_id", table_name="pagos")
    op.drop_table("pagos")
