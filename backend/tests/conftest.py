# tests/conftest.py
"""
Fixtures globales para la suite de tests de Food Store API.

Estrategia de aislamiento:
- engine_test (session-scope): crea el engine NullPool hacia food_store_test_db,
  crea todas las tablas al inicio y las elimina al terminar.
- clean_db (function-scope, autouse): TRUNCATE + RESTART IDENTITY CASCADE antes de
  cada test, luego re-siembra roles/estados/formas_pago y los 4 usuarios de test.
  Garantiza que cada test parte de un estado conocido y limpio.
- session (function-scope): Session directa sobre el engine de test, útil para
  verificar el estado de la DB después de llamadas a la API.
- client (function-scope): TestClient con get_session sobreescrito para usar el
  engine de test; también limpia los contadores del rate limiter antes de cada test.
- *_auth_headers (function-scope): hacen POST /api/v1/auth/login con el usuario
  de test correspondiente y devuelven {"Cookie": "access_token=..."}.

Para crear la base de test antes de correr:
    # Con docker-compose corriendo en :5433:
    docker exec postgres_tp5 createdb -U postgres food_store_test_db
    # O directamente:
    psql -U postgres -p 5433 -c "CREATE DATABASE food_store_test_db;"
"""
import os
import pytest

from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine
from fastapi.testclient import TestClient

# ── URL de la base de test ────────────────────────────────────────────────────
# Se puede sobreescribir con la variable TEST_DATABASE_URL del entorno.
# Por defecto apunta a las mismas credenciales del docker-compose, base distinta.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:1234@localhost:5433/food_store_test_db",
)

# Tablas en orden seguro para TRUNCATE CASCADE
_TODAS_LAS_TABLAS = (
    "pagos",
    "historial_estados_pedido",
    "detalle_pedidos",
    "pedidos",
    "direcciones_entrega",
    "producto_ingredientes",
    "producto_categorias",
    "productos",
    "ingredientes",
    "unidades_medida",
    "categorias",
    "usuario_roles",
    "refresh_tokens",
    "usuarios",
    "formas_pago",
    "estados_pedido",
    "roles",
)

# Credenciales de los 4 usuarios de test (sembrados en clean_db)
_USUARIOS_TEST = {
    "ADMIN":   ("admin_test@test.com",   "Test1234!"),
    "STOCK":   ("stock_test@test.com",   "Test1234!"),
    "PEDIDOS": ("pedidos_test@test.com", "Test1234!"),
    "CLIENT":  ("client_test@test.com",  "Test1234!"),
}


# ── engine_test ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def engine_test():
    """
    Motor de base de datos de test.
    - NullPool: sin pooling, cada conexión es independiente (evita estados compartidos).
    - Importa TODOS los modelos antes de create_all para que SQLModel los conozca.
    - Crea las tablas al empezar la sesión de test y las elimina al terminar.
    """
    # Registrar todos los modelos para que SQLModel.metadata los conozca
    import app.modules.usuarios.models                 # noqa: F401
    import app.modules.categorias.models               # noqa: F401
    import app.modules.ingredientes.models             # noqa: F401
    import app.modules.productos.models                # noqa: F401
    import app.modules.historial_estados_pedido.models # noqa: F401
    import app.modules.pedidos.models                  # noqa: F401
    import app.modules.direcciones.models              # noqa: F401
    import app.modules.pagos.models                     # noqa: F401

    engine = create_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


# ── Helpers de seed ───────────────────────────────────────────────────────────

def _seed_catalogo(session: Session) -> None:
    """
    Inserta los datos de catálogo que todos los tests necesitan:
    roles, estados de pedido y formas de pago.
    """
    from app.modules.usuarios.models import Rol
    from app.modules.pedidos.models import EstadoPedido, FormaPago
    from app.modules.ingredientes.models import UnidadMedida

    for obj in [
        Rol(codigo="ADMIN",   nombre="Administrador",      descripcion="Acceso total"),
        Rol(codigo="STOCK",   nombre="Gestión de Stock",   descripcion="Actualiza stock"),
        Rol(codigo="PEDIDOS", nombre="Gestión de Pedidos", descripcion="Avanza estados"),
        Rol(codigo="CLIENT",  nombre="Cliente",             descripcion="Datos propios"),
        EstadoPedido(codigo="PENDIENTE",  descripcion="Pedido recibido",  orden=1, es_terminal=False),
        EstadoPedido(codigo="CONFIRMADO", descripcion="Pago confirmado",  orden=2, es_terminal=False),
        EstadoPedido(codigo="EN_PREP",    descripcion="En preparación",   orden=3, es_terminal=False),
        EstadoPedido(codigo="ENTREGADO",  descripcion="Entregado",        orden=4, es_terminal=True),
        EstadoPedido(codigo="CANCELADO",  descripcion="Cancelado",        orden=5, es_terminal=True),
        FormaPago(codigo="EFECTIVO",      descripcion="Efectivo en local",     habilitado=True),
        FormaPago(codigo="TRANSFERENCIA", descripcion="Transferencia bancaria", habilitado=True),
        FormaPago(codigo="MERCADOPAGO",   descripcion="MercadoPago",            habilitado=True),
        UnidadMedida(codigo="KG",       nombre="kilogramo",      simbolo="kg",  tipo="MASA"),
        UnidadMedida(codigo="G",        nombre="gramo",          simbolo="g",   tipo="MASA"),
        UnidadMedida(codigo="L",        nombre="litro",          simbolo="L",   tipo="VOLUMEN"),
        UnidadMedida(codigo="ML",       nombre="mililitro",      simbolo="mL",  tipo="VOLUMEN"),
        UnidadMedida(codigo="UNIDADES", nombre="pieza",          simbolo="u",   tipo="UNIDAD"),
        UnidadMedida(codigo="DOC",      nombre="docena",         simbolo="doc", tipo="UNIDAD"),
        UnidadMedida(codigo="M2",       nombre="metro cuadrado", simbolo="m²",  tipo="AREA"),
    ]:
        session.add(obj)
    session.commit()


def _seed_usuarios_test(session: Session) -> None:
    """
    Crea los 4 usuarios de test — uno por rol — con contraseña Test1234!.
    ADMIN, STOCK y PEDIDOS no pueden crearse por /register (que solo asigna CLIENT);
    por eso se insertan directamente en la DB con hash de bcrypt.
    """
    from app.modules.usuarios.models import Usuario, UsuarioRol
    from app.modules.auth.security import hash_password

    for nombre, apellido, email, pwd, rol in [
        ("Admin",   "Test",  "admin_test@test.com",   "Test1234!", "ADMIN"),
        ("Stock",   "Test",  "stock_test@test.com",   "Test1234!", "STOCK"),
        ("Pedidos", "Test",  "pedidos_test@test.com", "Test1234!", "PEDIDOS"),
        ("Cliente", "Test",  "client_test@test.com",  "Test1234!", "CLIENT"),
    ]:
        u = Usuario(
            nombre=nombre, apellido=apellido, email=email,
            password_hash=hash_password(pwd),
        )
        session.add(u)
        session.flush()
        session.add(UsuarioRol(usuario_id=u.id, rol_codigo=rol, asignado_por_id=u.id))

    session.commit()


# ── clean_db ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def clean_db(engine_test):
    """
    Limpia todas las tablas antes de cada test y re-siembra el catálogo mínimo.
    autouse=True garantiza que todos los tests parten de un estado conocido,
    sin depender de que el orden de ejecución sea determinístico.
    """
    tablas = ", ".join(_TODAS_LAS_TABLAS)
    with engine_test.connect() as conn:
        conn.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))
        conn.commit()

    with Session(engine_test) as seed_session:
        _seed_catalogo(seed_session)
        _seed_usuarios_test(seed_session)

    yield


# ── session ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def session(engine_test, clean_db):
    """
    Sesión de DB directa para verificar el estado de la BD en los tests
    (por ejemplo, comprobar que el stock disminuyó tras confirmar un pedido).
    Usa el mismo engine_test, con NullPool → conexión fresca por cada test.
    """
    with Session(engine_test) as sess:
        yield sess


# ── client ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def client(engine_test, clean_db):
    """
    TestClient con la sesión de test inyectada vía dependency_overrides.

    - Cada request a la API crea una Session fresca del engine_test.
    - Los datos sembrados por clean_db son visibles inmediatamente (ya commiteados).
    - raise_server_exceptions=False: permite verificar respuestas de error (4xx/5xx)
      sin que TestClient levante la excepción.
    - Limpia los contadores del rate limiter antes de cada test para evitar
      que tests de rate limit arrastren estado a otros tests.
    """
    from app.main import app
    from app.core.database import get_session
    from app.core.rate_limit.rate_limit_middleware import RateLimitMiddleware

    RateLimitMiddleware.reset_all_limiters()

    def override_get_session():
        with Session(engine_test) as sess:
            yield sess

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.pop(get_session, None)


# ── Auth header fixtures ───────────────────────────────────────────────────────

def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    """
    Realiza el login y devuelve el header Cookie con el access_token.
    Falla de forma explícita si el login no retorna 200.
    """
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, (
        f"Login falló para {email}: {resp.status_code} {resp.text}"
    )
    token = resp.cookies.get("access_token")
    assert token, "No se recibió cookie access_token en el login"
    return {"Cookie": f"access_token={token}"}


@pytest.fixture(scope="function")
def admin_auth_headers(client: TestClient) -> dict[str, str]:
    """Headers con cookie access_token del usuario ADMIN de test."""
    email, pwd = _USUARIOS_TEST["ADMIN"]
    return _login(client, email, pwd)


@pytest.fixture(scope="function")
def stock_auth_headers(client: TestClient) -> dict[str, str]:
    """Headers con cookie access_token del usuario STOCK de test."""
    email, pwd = _USUARIOS_TEST["STOCK"]
    return _login(client, email, pwd)


@pytest.fixture(scope="function")
def pedidos_auth_headers(client: TestClient) -> dict[str, str]:
    """Headers con cookie access_token del usuario PEDIDOS de test."""
    email, pwd = _USUARIOS_TEST["PEDIDOS"]
    return _login(client, email, pwd)


@pytest.fixture(scope="function")
def client_auth_headers(client: TestClient) -> dict[str, str]:
    """Headers con cookie access_token del usuario CLIENT de test."""
    email, pwd = _USUARIOS_TEST["CLIENT"]
    return _login(client, email, pwd)

# ── Factories ─────────────────────────────────────────────────────────────────
# Insertan entidades directamente en la BD de test (rápido, sin pasar por la API
# ni requerir auth). Cada fixture devuelve una función `make(...)`; los datos se
# commitean en una Session propia y se devuelven ya desacoplados (dict primitivo)
# para evitar DetachedInstanceError. Los códigos/nombres llevan sufijo único.

@pytest.fixture(scope="function")
def producto_factory(engine_test, clean_db):
    """
    Crea un Producto TERMINADO con stock disponible en la BD de test.

    make(stock=10, precio="1000.00", nombre=None, disponible=True)
        → dict {id, codigo, nombre, precio_base, stock_cantidad}
    """
    from decimal import Decimal
    from uuid import uuid4

    from app.modules.productos.models import Producto, TipoProducto

    def make(
        stock: int = 10,
        precio: str = "1000.00",
        nombre: str | None = None,
        disponible: bool = True,
    ) -> dict:
        sufijo = uuid4().hex[:8]
        prod = Producto(
            codigo=f"PRODT{sufijo.upper()}",
            nombre=nombre or f"Producto Factory {sufijo}",
            tipo=TipoProducto.TERMINADO,
            precio_base=Decimal(precio),
            stock_cantidad=stock,
            disponible=disponible,
        )
        with Session(engine_test) as s:
            s.add(prod)
            s.commit()
            s.refresh(prod)
            return {
                "id": prod.id,
                "codigo": prod.codigo,
                "nombre": prod.nombre,
                "precio_base": str(prod.precio_base),
                "stock_cantidad": prod.stock_cantidad,
            }

    return make


@pytest.fixture(scope="function")
def pedido_factory(engine_test, clean_db):
    """
    Crea un Pedido en estado PENDIENTE con un DetallePedido en la BD de test.
    Acepta usuario_id y producto_id (el producto debe existir previamente).

    make(usuario_id, producto_id, cantidad=1, forma_pago_codigo="EFECTIVO",
         estado="PENDIENTE")
        → dict {id, codigo, estado_codigo, total}
    """
    from decimal import Decimal
    from uuid import uuid4

    from app.modules.pedidos.models import DetallePedido, Pedido
    from app.modules.productos.models import Producto

    _QUANT = Decimal("0.01")

    def make(
        usuario_id: int,
        producto_id: int,
        cantidad: int = 1,
        forma_pago_codigo: str = "EFECTIVO",
        estado: str = "PENDIENTE",
    ) -> dict:
        with Session(engine_test) as s:
            prod = s.get(Producto, producto_id)
            assert prod is not None, f"producto_id={producto_id} inexistente en la BD de test"

            precio = prod.precio_base
            subtotal = (precio * cantidad).quantize(_QUANT)

            pedido = Pedido(
                codigo=f"PEDF{uuid4().hex[:8].upper()}",
                usuario_id=usuario_id,
                forma_pago_codigo=forma_pago_codigo,
                estado_codigo=estado,
                subtotal=subtotal,
                descuento=Decimal("0.00"),
                costo_envio=Decimal("0.00"),
                total=subtotal,
            )
            s.add(pedido)
            s.flush()

            s.add(DetallePedido(
                pedido_id=pedido.id,
                producto_id=producto_id,
                cantidad=cantidad,
                nombre_snapshot=prod.nombre,
                precio_snapshot=precio,
                subtotal_snap=subtotal,
            ))
            s.commit()
            s.refresh(pedido)
            return {
                "id": pedido.id,
                "codigo": pedido.codigo,
                "estado_codigo": pedido.estado_codigo,
                "total": str(pedido.total),
            }

    return make