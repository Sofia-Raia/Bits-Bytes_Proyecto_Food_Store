"""add_imagenes_tiempo_prep_es_opcional

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-28 00:03:00.000000

Tres cambios al catálogo de productos:
  1. productos.imagen_url TEXT → DROP; ADD imagenes_url TEXT[] NOT NULL DEFAULT '{}'
  2. productos.tiempo_prep_min INT NULL
  3. producto_ingredientes.es_opcional BOOLEAN NOT NULL DEFAULT false

EN_CAMINO no requiere migración: es entrada de catálogo gestionada por seed.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Galería de imágenes: reemplazar imagen_url singular por array
    op.drop_column("productos", "imagen_url")
    op.add_column(
        "productos",
        sa.Column(
            "imagenes_url",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )

    # 2. Tiempo de preparación estimado (opcional)
    op.add_column(
        "productos",
        sa.Column("tiempo_prep_min", sa.Integer(), nullable=True),
    )

    # 3. Ingrediente opcional (puede pedirse como extra)
    op.add_column(
        "producto_ingredientes",
        sa.Column(
            "es_opcional",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("producto_ingredientes", "es_opcional")
    op.drop_column("productos", "tiempo_prep_min")
    op.drop_column("productos", "imagenes_url")
    op.add_column(
        "productos",
        sa.Column("imagen_url", sa.Text(), nullable=True),
    )
