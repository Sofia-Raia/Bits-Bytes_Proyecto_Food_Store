"""complete_pago_fields_erd_v7

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-10 00:00:00.000000

ERD v7 — completa la tabla `pagos`:
- transaction_amount NUMERIC(12,2) NULL — monto cobrado por MercadoPago.
- external_reference VARCHAR(100) UNIQUE NULL — referencia que viaja a MP.
- payment_method_id VARCHAR(50) NULL — medio usado (visa, master, account_money...).
- mp_payment_id pasa a UNIQUE (un pago de MP se registra una sola vez).
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pagos", sa.Column("transaction_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("pagos", sa.Column("external_reference", sa.String(length=100), nullable=True))
    op.add_column("pagos", sa.Column("payment_method_id", sa.String(length=50), nullable=True))

    op.create_index("ix_pagos_external_reference", "pagos", ["external_reference"])
    op.create_unique_constraint("uq_pagos_external_reference", "pagos", ["external_reference"])
    # mp_payment_id pasa a único (antes solo index)
    op.create_unique_constraint("uq_pagos_mp_payment_id", "pagos", ["mp_payment_id"])


def downgrade() -> None:
    op.drop_constraint("uq_pagos_mp_payment_id", "pagos", type_="unique")
    op.drop_constraint("uq_pagos_external_reference", "pagos", type_="unique")
    op.drop_index("ix_pagos_external_reference", table_name="pagos")
    op.drop_column("pagos", "payment_method_id")
    op.drop_column("pagos", "external_reference")
    op.drop_column("pagos", "transaction_amount")
