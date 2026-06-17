"""add_unidades_medida_catalog

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-09 00:00:00.000000

ERD v7.2 — UnidadMedida como tabla «Catalog».
- Crea la tabla `unidades_medida` y la siembra con las 7 unidades del ERD.
- `ingredientes`: reemplaza la columna enum `unidad_medida` por `unidad_medida_id` (FK),
  con backfill mapeando el valor del enum (KG/L/UNIDADES) al id del catálogo.
- `productos`: agrega `unidad_venta_id` (FK, NULL) — unidad de venta del ERD.
- `producto_ingredientes`: agrega `unidad_medida_id` (FK, NN), backfill desde la
  unidad del ingrediente.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


_UNIDADES = [
    ("KG", "kilogramo", "kg", "MASA"),
    ("G", "gramo", "g", "MASA"),
    ("L", "litro", "L", "VOLUMEN"),
    ("ML", "mililitro", "mL", "VOLUMEN"),
    ("UNIDADES", "pieza", "u", "UNIDAD"),
    ("DOC", "docena", "doc", "UNIDAD"),
    ("M2", "metro cuadrado", "m²", "AREA"),
]


def upgrade() -> None:
    # 1. Tabla catálogo unidades_medida
    op.create_table(
        "unidades_medida",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.Column("simbolo", sa.String(length=10), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo", name="uq_unidades_medida_codigo"),
        sa.UniqueConstraint("nombre", name="uq_unidades_medida_nombre"),
        sa.UniqueConstraint("simbolo", name="uq_unidades_medida_simbolo"),
    )
    op.create_index("ix_unidades_medida_codigo", "unidades_medida", ["codigo"])

    # 2. Seed de las 7 unidades del ERD
    um = sa.table(
        "unidades_medida",
        sa.column("codigo", sa.String),
        sa.column("nombre", sa.String),
        sa.column("simbolo", sa.String),
        sa.column("tipo", sa.String),
    )
    op.bulk_insert(
        um,
        [{"codigo": c, "nombre": n, "simbolo": s, "tipo": t} for (c, n, s, t) in _UNIDADES],
    )

    # 3. ingredientes: enum unidad_medida → unidad_medida_id (FK)
    op.add_column("ingredientes", sa.Column("unidad_medida_id", sa.Integer(), nullable=True))
    # Backfill: mapear el valor del enum al id del catálogo por código
    op.execute(
        """
        UPDATE ingredientes i
        SET unidad_medida_id = um.id
        FROM unidades_medida um
        WHERE um.codigo = i.unidad_medida::text
        """
    )
    # Cualquier remanente sin match → UNIDADES (defensivo)
    op.execute(
        """
        UPDATE ingredientes
        SET unidad_medida_id = (SELECT id FROM unidades_medida WHERE codigo = 'UNIDADES')
        WHERE unidad_medida_id IS NULL
        """
    )
    op.alter_column("ingredientes", "unidad_medida_id", nullable=False)
    op.create_index("ix_ingredientes_unidad_medida_id", "ingredientes", ["unidad_medida_id"])
    op.create_foreign_key(
        "fk_ingredientes_unidad_medida_id", "ingredientes", "unidades_medida",
        ["unidad_medida_id"], ["id"],
    )
    op.drop_column("ingredientes", "unidad_medida")
    # Eliminar el tipo enum de Postgres si quedó huérfano
    op.execute("DROP TYPE IF EXISTS unidadmedida")

    # 4. productos.unidad_venta_id (FK, NULL)
    op.add_column("productos", sa.Column("unidad_venta_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_productos_unidad_venta_id", "productos", "unidades_medida",
        ["unidad_venta_id"], ["id"],
    )

    # 5. producto_ingredientes.unidad_medida_id (FK, NN) — backfill desde el ingrediente
    op.add_column("producto_ingredientes", sa.Column("unidad_medida_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE producto_ingredientes pi
        SET unidad_medida_id = i.unidad_medida_id
        FROM ingredientes i
        WHERE i.id = pi.ingrediente_id
        """
    )
    op.execute(
        """
        UPDATE producto_ingredientes
        SET unidad_medida_id = (SELECT id FROM unidades_medida WHERE codigo = 'UNIDADES')
        WHERE unidad_medida_id IS NULL
        """
    )
    op.alter_column("producto_ingredientes", "unidad_medida_id", nullable=False)
    op.create_foreign_key(
        "fk_producto_ingredientes_unidad_medida_id", "producto_ingredientes", "unidades_medida",
        ["unidad_medida_id"], ["id"],
    )


def downgrade() -> None:
    # producto_ingredientes
    op.drop_constraint("fk_producto_ingredientes_unidad_medida_id", "producto_ingredientes", type_="foreignkey")
    op.drop_column("producto_ingredientes", "unidad_medida_id")

    # productos
    op.drop_constraint("fk_productos_unidad_venta_id", "productos", type_="foreignkey")
    op.drop_column("productos", "unidad_venta_id")

    # ingredientes: recrear columna enum y backfill inverso
    enum_um = sa.Enum("KG", "L", "UNIDADES", name="unidadmedida")
    enum_um.create(op.get_bind(), checkfirst=True)
    op.add_column("ingredientes", sa.Column("unidad_medida", enum_um, nullable=True))
    op.execute(
        """
        UPDATE ingredientes i
        SET unidad_medida = (
            CASE WHEN um.codigo IN ('KG', 'L', 'UNIDADES') THEN um.codigo ELSE 'UNIDADES' END
        )::unidadmedida
        FROM unidades_medida um
        WHERE um.id = i.unidad_medida_id
        """
    )
    op.alter_column("ingredientes", "unidad_medida", nullable=False)
    op.drop_constraint("fk_ingredientes_unidad_medida_id", "ingredientes", type_="foreignkey")
    op.drop_index("ix_ingredientes_unidad_medida_id", table_name="ingredientes")
    op.drop_column("ingredientes", "unidad_medida_id")

    # catálogo
    op.drop_index("ix_unidades_medida_codigo", table_name="unidades_medida")
    op.drop_table("unidades_medida")
