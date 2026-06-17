"""
alembic/env.py
==============
Configura Alembic para usar la misma BD y los mismos modelos que FastAPI.

Puntos clave:
- La URL se toma de `app.core.config.settings` (leyendo .env) para no hardcodear
  credenciales en alembic.ini.
- Se importan TODOS los módulos de modelos antes de acceder a `target_metadata`,
  de modo que Alembic detecte las tablas al correr --autogenerate.
- El orden de imports refleja las dependencias de FK: primero usuarios, luego
  categorías, ingredientes, productos, historial y pedidos.
"""

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Agregar el directorio backend/ al path para que los imports de `app` funcionen
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Cargar settings (lee .env automáticamente via pydantic-settings) ──────────
from app.core.config import settings  # noqa: E402

# ── Importar todos los modelos para que SQLModel los registre en metadata ──────
# El orden importa: referenciado antes de referenciador.
import app.modules.usuarios.models                    # noqa: F401
import app.modules.categorias.models                  # noqa: F401
import app.modules.ingredientes.models                # noqa: F401
import app.modules.productos.models                   # noqa: F401
import app.modules.historial_estados_pedido.models    # noqa: F401
import app.modules.pedidos.models                     # noqa: F401
import app.modules.direcciones.models                 # noqa: F401
import app.modules.pagos.models                        # noqa: F401

from sqlmodel import SQLModel  # noqa: E402

# Alembic Config — objeto que accede a alembic.ini
config = context.config

# Inyectar la URL real (lee .env) sobreescribiendo el placeholder de alembic.ini
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configurar logging desde alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata objetivo para --autogenerate
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """
    Modo offline: genera SQL sin conectarse a la BD.
    Útil para revisar las migraciones antes de aplicarlas.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Comparar tipos de columna para detectar cambios de Numeric/VARCHAR etc.
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Modo online: se conecta a la BD y aplica las migraciones directamente.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Detectar cambios en tipos de columna (Numeric, Enum, etc.)
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
