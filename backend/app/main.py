# main.py
"""
Punto de entrada de la aplicación Food Store API.

Con Alembic las tablas se crean/migran con `alembic upgrade head` antes de
iniciar el servidor. El `create_db_and_tables()` ya NO se llama en el lifespan
para evitar que SQLModel sobrescriba cambios de tipo generados por Alembic
(ej: Numeric(12,2) → DOUBLE PRECISION si se corre create_all sobre una BD existente).

Para desarrollo local sin Alembic (primer arranque desde cero):
    alembic upgrade head   ← crea las tablas
    python seed.py         ← siembra datos iniciales
    python -m fastapi dev app/main.py
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import setup_logging
from app.core.exceptions.exception_handlers import register_exception_handlers
from app.core.middleware.logging_middleware import LoggingMiddleware
from app.core.middleware.timing_middleware import TimingMiddleware
from app.core.rate_limit.rate_limit_middleware import RateLimitMiddleware

from app.modules.auth.router import router as auth_router
from app.modules.direcciones.router import router as direcciones_router
from app.modules.health.router import router as health_router
from app.modules.ingredientes.router import router as ingredientes_router
from app.modules.categorias.router import router as categorias_router
from app.modules.pedidos.router import router as pedidos_router
from app.modules.productos.router import router as productos_router
from app.modules.usuarios.router import router as usuarios_router
from app.modules.pagos.router import router as pagos_router
from app.modules.uploads.router import router as uploads_router
from app.modules.estadisticas.router import router as estadisticas_router

# ── Registrar todos los modelos (necesario para Alembic autogenerate y para
#    que SQLModel los conozca en tiempo de ejecución) ─────────────────────────
import app.modules.usuarios.models                    
import app.modules.categorias.models                  
import app.modules.ingredientes.models                
import app.modules.productos.models                   
import app.modules.historial_estados_pedido.models    
import app.modules.pedidos.models                     
import app.modules.direcciones.models                 
import app.modules.pagos.models                        

# Configurar logging antes de todo lo demás
setup_logging(settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Las tablas se gestionan con Alembic (`alembic upgrade head`).
    # No llamamos a create_db_and_tables() aquí para respetar las migraciones.
    yield


app = FastAPI(
    title="Food Store API",
    description="API para gestión de catálogo, pedidos y trazabilidad",
    version="2.0.0",
    lifespan=lifespan,
)

# ── Exception handlers ────────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Middleware stack ──────────────────────────────────────────────────────────
# Starlette procesa los middleware en orden LIFO (el último agregado es el más externo).
# Orden de ejecución de requests:
#   CORSMiddleware → TimingMiddleware → LoggingMiddleware → RateLimitMiddleware → routes
#
# El CORSMiddleware queda como envoltorio exterior para que los preflight OPTIONS
# sean respondidos antes de pasar por rate limit y logging.

app.add_middleware(
    RateLimitMiddleware,
    settings=settings,
)

app.add_middleware(LoggingMiddleware)

app.add_middleware(TimingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["X-Request-ID", "Server-Timing"],
    max_age=600,  # cachea preflight 10 min
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(auth_router,         prefix="/api/v1/auth",        tags=["auth"])
app.include_router(usuarios_router,     prefix="/api/v1/usuarios",    tags=["usuarios"])
app.include_router(categorias_router,   prefix="/api/v1/categorias",  tags=["categorias"])
app.include_router(ingredientes_router, prefix="/api/v1/ingredientes", tags=["ingredientes"])
app.include_router(productos_router,    prefix="/api/v1/productos",   tags=["productos"])
app.include_router(pedidos_router,      prefix="/api/v1/pedidos",     tags=["pedidos"])
app.include_router(direcciones_router,  prefix="/api/v1/direcciones", tags=["direcciones"])
app.include_router(pagos_router,        prefix="/api/v1/pagos",       tags=["pagos"])
app.include_router(uploads_router,      prefix="/api/v1/uploads",      tags=["uploads"])
app.include_router(estadisticas_router, prefix="/api/v1/estadisticas", tags=["estadisticas"])
