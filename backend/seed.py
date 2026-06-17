"""
seed.py — Carga datos iniciales en los catálogos.
Ejecutar después de aplicar las migraciones:

    alembic upgrade head   ← crea las tablas (reemplaza create_all)
    python seed.py         ← siembra datos iniciales

⚠ Si ya tenés una BD de una versión anterior (con float):
    docker compose down -v   ← elimina el volumen y los datos
    docker compose up -d     ← reinicia PostgreSQL limpio
    alembic upgrade head
    python seed.py
"""
import os
from decimal import Decimal

from dotenv import load_dotenv
from sqlmodel import Session, create_engine, select

from app.core.config import settings
from app.modules.pedidos.models import FormaPago, EstadoPedido

load_dotenv()

# Usa DATABASE_URL si está definida en el entorno; si no, la arma desde las
# variables postgres_* (misma fuente que la app y Alembic via settings).
engine = create_engine(os.getenv("DATABASE_URL") or settings.DATABASE_URL)


# FormaPago: EFECTIVO, TRANSFERENCIA y MERCADOPAGO
FORMAS_PAGO = [
    FormaPago(codigo="EFECTIVO",      descripcion="Efectivo en local",     habilitado=True),
    FormaPago(codigo="TRANSFERENCIA", descripcion="Transferencia bancaria", habilitado=True),
    FormaPago(codigo="MERCADOPAGO",   descripcion="MercadoPago",            habilitado=True),
]

ESTADOS_PEDIDO = [
    EstadoPedido(codigo="PENDIENTE",  descripcion="Pedido recibido, sin confirmar",       orden=1, es_terminal=False),
    EstadoPedido(codigo="CONFIRMADO", descripcion="Pago confirmado",                      orden=2, es_terminal=False),
    EstadoPedido(codigo="EN_PREP",    descripcion="En preparación",                       orden=3, es_terminal=False),
    EstadoPedido(codigo="ENTREGADO",  descripcion="Entregado al cliente",                 orden=4, es_terminal=True),
    EstadoPedido(codigo="CANCELADO",  descripcion="Pedido cancelado",                     orden=5, es_terminal=True),
]

# UnidadMedida (catálogo ERD «Catalog»). codigo = clave semántica usada por la API.
# (codigo, nombre, simbolo, tipo)
UNIDADES_MEDIDA = [
    ("KG",       "kilogramo",      "kg",  "MASA"),
    ("G",        "gramo",          "g",   "MASA"),
    ("L",        "litro",          "L",   "VOLUMEN"),
    ("ML",       "mililitro",      "mL",  "VOLUMEN"),
    ("UNIDADES", "pieza",          "u",   "UNIDAD"),
    ("DOC",      "docena",         "doc", "UNIDAD"),
    ("M2",       "metro cuadrado", "m²",  "AREA"),
]


def _seed_roles_y_usuarios() -> None:
    """Crea roles y usuarios por defecto si no existen (T-B17)."""
    from app.modules.auth.models import Rol, Usuario, UsuarioRol
    from app.modules.auth.security import hash_password

    ROLES = [
        Rol(codigo="ADMIN",   nombre="Administrador",      descripcion="Acceso total sin restricciones"),
        Rol(codigo="STOCK",   nombre="Gestión de Stock",   descripcion="Actualiza stock y disponibilidad"),
        Rol(codigo="PEDIDOS", nombre="Gestión de Pedidos", descripcion="Avanza estados CONFIRMADO→ENTREGADO"),
        Rol(codigo="CLIENT",  nombre="Cliente",             descripcion="Opera solo sus propios datos"),
    ]

    USUARIOS_DEFAULT = [
        {
            "nombre": "Admin", "apellido": "Sistema",
            "email": "admin@foodstore.com", "password": "admin123",
            "roles": ["ADMIN"],
        },
        {
            "nombre": "Stock", "apellido": "Sistema",
            "email": "stock@foodstore.com", "password": "stock123",
            "roles": ["STOCK"],
        },
        {
            "nombre": "Pedidos", "apellido": "Sistema",
            "email": "pedidos@foodstore.com", "password": "pedidos123",
            "roles": ["PEDIDOS"],
        },
        {
            "nombre": "Cliente", "apellido": "Demo",
            "email": "cliente@foodstore.com", "password": "cliente123",
            "roles": ["CLIENT"],
        },
    ]

    with Session(engine) as session:
        for rol in ROLES:
            if not session.get(Rol, rol.codigo):
                session.add(rol)
                print(f"  ✓ Rol: {rol.codigo}")
            else:
                print(f"  · Rol ya existe: {rol.codigo}")
        session.flush()

        for u_data in USUARIOS_DEFAULT:
            exists = session.exec(
                select(Usuario).where(Usuario.email == u_data["email"])
            ).first()
            if not exists:
                user = Usuario(
                    nombre=u_data["nombre"],
                    apellido=u_data["apellido"],
                    email=u_data["email"],
                    password_hash=hash_password(u_data["password"]),
                )
                session.add(user)
                session.flush()
                for rol_codigo in u_data["roles"]:
                    session.add(UsuarioRol(usuario_id=user.id, rol_codigo=rol_codigo))
                print(f"  ✓ Usuario: {u_data['email']}")
            else:
                print(f"  · Usuario ya existe: {u_data['email']}")
        session.commit()


def _seed_catalogo_fastfood() -> None:
    """
    Siembra el catálogo completo de un food store de comida rápida.

    Árbol de categorías:
      Hamburguesas
        ├── Clásicas
        └── Especiales
      Papas y Snacks
      Bebidas
        └── Gaseosas
      Postres

    Ingredientes: 15 (mix KG / L / UNIDADES, con alergenos marcados).
    Productos: 12 (7 MANUFACTURADOS con ingredientes + 5 TERMINADOS).

    Idempotente: si ya existe alguna categoría, saltea todo el bloque.
    """
    from app.modules.categorias.models import Categoria
    from app.modules.ingredientes.models import Ingrediente, UnidadMedida
    from app.modules.productos.models import (
        Producto, ProductoCategoria, ProductoIngrediente, TipoProducto,
    )
    from app.core.codigo import generar_codigo

    with Session(engine) as session:
        if session.exec(select(Categoria)).first():
            print("  · Catálogo ya sembrado, saltando.")
            return

        # ── 1. Categorías ─────────────────────────────────────────────────────

        def nueva_cat(nombre, descripcion, parent=None):
            codigo = generar_codigo(session, "categoria")
            cat = Categoria(
                codigo=codigo,
                nombre=nombre,
                descripcion=descripcion,
                parent_id=parent.id if parent else None,
            )
            session.add(cat)
            session.flush()
            indent = "      " if parent else "    "
            print(f"{indent}✓ {nombre} ({codigo})")
            return cat

        print("  Categorías:")
        c_hamburguesas = nueva_cat("Hamburguesas",   "Nuestras hamburguesas artesanales")
        c_clasicas     = nueva_cat("Clásicas",       "Las favoritas de siempre",          parent=c_hamburguesas)
        c_especiales   = nueva_cat("Especiales",     "Combinaciones únicas y de autor",   parent=c_hamburguesas)
        c_papas        = nueva_cat("Papas y Snacks", "Papas fritas y snacks salados")
        c_bebidas      = nueva_cat("Bebidas",        "Bebidas frías para acompañar")
        c_gaseosas     = nueva_cat("Gaseosas",       "Bebidas gaseosas en lata o vaso",   parent=c_bebidas)
        c_postres      = nueva_cat("Postres",        "Para cerrar con dulzura")

        # ── 2. Ingredientes ───────────────────────────────────────────────────

        # Mapa codigo → UnidadMedida (el catálogo se sembró en seed())
        unidades = {u.codigo: u for u in session.exec(select(UnidadMedida)).all()}

        # (nombre, descripcion, es_alergeno, costo NUMERIC(12,4), unidad_codigo)
        INGR_DATA = [
            ("Pan brioche",     "Pan tipo brioche para hamburguesas",       True,  Decimal("3500.0000"), "KG"),
            ("Carne vacuna",    "Medallón de carne molida 80/20",           False, Decimal("8000.0000"), "KG"),
            ("Lechuga",         "Lechuga fresca en hojas",                  False, Decimal("500.0000"),  "KG"),
            ("Tomate",          "Tomate fresco en rodajas",                 False, Decimal("600.0000"),  "KG"),
            ("Cebolla",         "Cebolla blanca en aros",                   False, Decimal("300.0000"),  "KG"),
            ("Queso cheddar",   "Queso cheddar en fetas",                   True,  Decimal("9000.0000"), "KG"),
            ("Mayonesa",        "Mayonesa casera (contiene huevo)",         True,  Decimal("4000.0000"), "L"),
            ("Ketchup",         "Ketchup de tomate",                        False, Decimal("2000.0000"), "L"),
            ("Bacon",           "Panceta ahumada en fetas finas",           False, Decimal("12000.0000"),"KG"),
            ("Pepinillos",      "Pepinillos en vinagre en rodajas",         False, Decimal("2000.0000"), "KG"),
            ("Papa bastón",     "Papa pre-frita en bastones",               False, Decimal("1800.0000"), "KG"),
            ("Aceite vegetal",  "Aceite vegetal de girasol para fritura",   False, Decimal("3000.0000"), "L"),
            ("Sal fina",        "Sal fina de mesa",                         False, Decimal("200.0000"),  "KG"),
            ("Pollo fileteado", "Pechuga de pollo fileteada y marinada",    False, Decimal("6000.0000"), "KG"),
            ("Salsa BBQ",       "Salsa barbecue ahumada",                   False, Decimal("3000.0000"), "L"),
        ]

        print("  Ingredientes:")
        ingr = {}  # nombre → Ingrediente (para linkear en productos)
        for nombre, descripcion, es_alergeno, costo, unidad_codigo in INGR_DATA:
            codigo = generar_codigo(session, "ingrediente")
            obj = Ingrediente(
                codigo=codigo,
                nombre=nombre,
                descripcion=descripcion,
                es_alergeno=es_alergeno,
                costo=costo,
                unidad_medida_id=unidades[unidad_codigo].id,
                stock_cantidad=Decimal("100.000"),  
            )
            session.add(obj)
            session.flush()
            ingr[nombre] = obj
            alg = " ⚠ alergeno" if es_alergeno else ""
            print(f"    ✓ {nombre} ({codigo}) — {unidad_codigo}{alg}")

        # ── 3. Productos ──────────────────────────────────────────────────────

        def nuevo_prod(
            nombre, descripcion, tipo, precio_base, stock,
            cats_principal,      # [Categoria, ...]  — primero = es_principal=True
            cats_extra=None,     # [Categoria, ...]  — es_principal=False
            receta=None,         # [(nombre_ingr, cantidad_str, es_removible), ...]
        ):
            """
            Crea un Producto y sus relaciones M2M de categorías e ingredientes.
            Todos los productos se venden por UNIDADES.

            Coherencia de stock (RN-PE / T3.6):
            - TERMINADO: el stock del producto es el que se valida y descuenta en cada
              pedido → se usa `stock` tal cual.
            - MANUFACTURADO: el pedido NO descuenta el stock del producto, sino el de
              sus INGREDIENTES. Por eso el stock mostrado se clampa al máximo realmente
              producible con el stock de ingredientes sembrado, para que el catálogo no
              prometa más unidades de las que los ingredientes permiten fabricar.
            """
            stock_final = stock
            if tipo == TipoProducto.MANUFACTURADO and receta:
                # máximo producible = piso( min( stock_ingrediente / cantidad_receta ) )
                producible = min(
                    int(ingr[n].stock_cantidad // Decimal(c))
                    for (n, c, _r) in receta
                )
                stock_final = min(stock, producible)
                if producible < stock:
                    print(f"      ⚠ {nombre}: stock {stock} > producible {producible} "
                          f"(limitado por ingredientes) → se usa {stock_final}")

            codigo = generar_codigo(session, "producto")
            prod = Producto(
                codigo=codigo,
                nombre=nombre,
                descripcion=descripcion,
                tipo=tipo,
                imagenes_url=[],       # sin imagen por defecto en seed
                tiempo_prep_min=None,  # opcional, no se seed
                precio_base=precio_base,
                stock_cantidad=stock_final,
                disponible=True,
            )
            session.add(prod)
            session.flush()

            # Categorías
            for i, cat in enumerate(cats_principal):
                session.add(ProductoCategoria(
                    producto_id=prod.id,
                    categoria_id=cat.id,
                    es_principal=(i == 0),   # solo la primera es principal
                ))
            for cat in (cats_extra or []):
                session.add(ProductoCategoria(
                    producto_id=prod.id,
                    categoria_id=cat.id,
                    es_principal=False,
                ))

            # Ingredientes (solo MANUFACTURADO)
            for nombre_i, cantidad_str, es_removible in (receta or []):
                ing_obj = ingr[nombre_i]
                session.add(ProductoIngrediente(
                    producto_id=prod.id,
                    ingrediente_id=ing_obj.id,
                    cantidad=Decimal(cantidad_str),
                    unidad_medida_id=ing_obj.unidad_medida_id,
                    es_removible=es_removible,
                    es_opcional=False,
                ))

            session.flush()
            print(f"    ✓ {nombre} ({codigo})")
            return prod

        MAN = TipoProducto.MANUFACTURADO
        TER = TipoProducto.TERMINADO

        print("  Productos:")

        # ── Hamburguesas Clásicas ─────────────────────────────
        nuevo_prod(
            "Hamburguesa Clásica",
            "Medallón de carne vacuna con lechuga, tomate, ketchup y mayonesa",
            MAN, Decimal("2500.00"), 50,
            cats_principal=[c_clasicas],
            cats_extra=[c_hamburguesas],
            receta=[
                ("Pan brioche",  "0.1200", False),
                ("Carne vacuna", "0.1500", False),
                ("Lechuga",      "0.0500", True),
                ("Tomate",       "0.0600", True),
                ("Ketchup",      "0.0200", True),
                ("Mayonesa",     "0.0200", True),
            ],
        )

        nuevo_prod(
            "Hamburguesa Doble",
            "Doble medallón con doble cheddar, pepinillos, ketchup y mayonesa",
            MAN, Decimal("3200.00"), 40,
            cats_principal=[c_clasicas],
            cats_extra=[c_hamburguesas],
            receta=[
                ("Pan brioche",   "0.1200", False),
                ("Carne vacuna",  "0.3000", False),   # doble medallón
                ("Queso cheddar", "0.0800", True),    # doble queso
                ("Pepinillos",    "0.0300", True),
                ("Ketchup",       "0.0200", True),
                ("Mayonesa",      "0.0200", True),
            ],
        )

        # ── Hamburguesas Especiales ───────────────────────────
        nuevo_prod(
            "Hamburguesa BBQ",
            "Medallón con bacon, cebolla, queso cheddar y salsa BBQ ahumada",
            MAN, Decimal("3500.00"), 35,
            cats_principal=[c_especiales],
            cats_extra=[c_hamburguesas],
            receta=[
                ("Pan brioche",   "0.1200", False),
                ("Carne vacuna",  "0.1500", False),
                ("Bacon",         "0.0500", True),
                ("Cebolla",       "0.0400", True),
                ("Queso cheddar", "0.0400", True),
                ("Salsa BBQ",     "0.0300", True),
            ],
        )

        nuevo_prod(
            "Hamburguesa de Pollo",
            "Pechuga de pollo fileteada con lechuga, tomate y mayonesa",
            MAN, Decimal("2800.00"), 40,
            cats_principal=[c_especiales],
            cats_extra=[c_hamburguesas],
            receta=[
                ("Pan brioche",     "0.1200", False),
                ("Pollo fileteado", "0.1500", False),
                ("Lechuga",         "0.0500", True),
                ("Tomate",          "0.0600", True),
                ("Mayonesa",        "0.0200", True),
            ],
        )

        # ── Papas y Snacks ────────────────────────────────────
        nuevo_prod(
            "Papas Fritas Chicas",
            "Bastones de papa crocantes — porción chica",
            MAN, Decimal("1200.00"), 80,
            cats_principal=[c_papas],
            receta=[
                ("Papa bastón",    "0.2000", False),
                ("Aceite vegetal", "0.0500", False),
                ("Sal fina",       "0.0050", True),
            ],
        )

        nuevo_prod(
            "Papas Fritas Grandes",
            "Bastones de papa crocantes — porción grande",
            MAN, Decimal("1600.00"), 80,
            cats_principal=[c_papas],
            receta=[
                ("Papa bastón",    "0.3500", False),
                ("Aceite vegetal", "0.0800", False),
                ("Sal fina",       "0.0050", True),
            ],
        )

        nuevo_prod(
            "Papas con Cheddar",
            "Papas fritas bañadas en salsa de queso cheddar",
            MAN, Decimal("1900.00"), 60,
            cats_principal=[c_papas],
            receta=[
                ("Papa bastón",    "0.3000", False),
                ("Aceite vegetal", "0.0800", False),
                ("Sal fina",       "0.0050", True),
                ("Queso cheddar",  "0.0800", True),
            ],
        )

        # ── Bebidas (TERMINADO — productos envasados) ─────────
        nuevo_prod(
            "Gaseosa Cola",
            "Bebida gaseosa sabor cola — 500 ml",
            TER, Decimal("800.00"), 100,
            cats_principal=[c_gaseosas],
            cats_extra=[c_bebidas],
        )

        nuevo_prod(
            "Gaseosa Naranja",
            "Bebida gaseosa sabor naranja — 500 ml",
            TER, Decimal("800.00"), 100,
            cats_principal=[c_gaseosas],
            cats_extra=[c_bebidas],
        )

        nuevo_prod(
            "Agua Mineral",
            "Agua mineral sin gas — 500 ml",
            TER, Decimal("600.00"), 120,
            cats_principal=[c_bebidas],
        )

        # ── Postres (TERMINADO) ───────────────────────────────
        nuevo_prod(
            "Helado Vainilla",
            "Copa de helado artesanal sabor vainilla",
            TER, Decimal("1500.00"), 50,
            cats_principal=[c_postres],
        )

        nuevo_prod(
            "Helado Chocolate",
            "Copa de helado artesanal sabor chocolate",
            TER, Decimal("1500.00"), 50,
            cats_principal=[c_postres],
        )

        session.commit()
        print("  Catálogo sembrado exitosamente.")


def _seed_pedidos_demo() -> None:
    """
    Siembra ~25 pedidos de demostración con fechas distribuidas en los últimos
    45 días para que las estadísticas y el dashboard del video muestren datos reales.

    Crea:
    - 19 pedidos ENTREGADO  (base de ingresos)
    -  3 pedidos CANCELADO  (excluidos de ingresos — valida EST-01)
    -  1 pedido  EN_PREP    (activo en cocina)
    -  1 pedido  CONFIRMADO (pago confirmado, aún no en prep)
    -  1 pedido  PENDIENTE  (sin confirmar)
    - Mix MERCADOPAGO / EFECTIVO para el gráfico de ingresos por forma de pago
    - Registro Pago con mp_status="approved" para cada pedido MP confirmado

    Idempotente: si ya existe algún pedido, saltea todo el bloque.
    """
    import uuid
    import random
    from datetime import datetime, timedelta, timezone

    from app.modules.auth.models import Usuario
    from app.modules.pedidos.models import Pedido, DetallePedido
    from app.modules.historial_estados_pedido.models import HistorialEstadoPedido
    from app.modules.pagos.models import Pago
    from app.modules.productos.models import Producto
    from app.core.codigo import generar_codigo

    with Session(engine) as session:
        if session.exec(select(Pedido)).first():
            print("  · Pedidos demo ya sembrados, saltando.")
            return

        cliente = session.exec(select(Usuario).where(Usuario.email == "cliente@foodstore.com")).first()
        admin   = session.exec(select(Usuario).where(Usuario.email == "admin@foodstore.com")).first()
        if not cliente or not admin:
            print("  ✗ Usuarios no encontrados. Ejecutá seed() antes de _seed_pedidos_demo().")
            return

        productos = session.exec(select(Producto)).all()
        if not productos:
            print("  ✗ Productos no encontrados. Ejecutá _seed_catalogo_fastfood() primero.")
            return

        hoy = datetime.now(timezone.utc)
        COSTO_ENVIO = Decimal("500.00")

        # Cada tupla: (días_atrás, estado_final, forma_pago, [(idx_producto, cantidad), ...])
        # Los índices referencian la lista `productos` (12 productos sembrados: 0-11).
        PEDIDOS_DEMO = [
            # ── Hace ~6 semanas ──────────────────────────────────────────────
            (45, "ENTREGADO",  "MERCADOPAGO", [(0, 2), (4, 1)]),   # Clásica x2 + Papas Ch.
            (43, "ENTREGADO",  "EFECTIVO",    [(1, 1), (7, 2)]),   # Doble + Gaseosa Cola x2
            (41, "ENTREGADO",  "MERCADOPAGO", [(2, 1), (5, 1)]),   # BBQ + Papas Gr.
            (40, "CANCELADO",  "EFECTIVO",    [(0, 1)]),            # cancelado — no suma
            # ── Hace ~4-5 semanas ────────────────────────────────────────────
            (38, "ENTREGADO",  "MERCADOPAGO", [(3, 1), (6, 1), (8, 1)]),  # Pollo + Cheddar + Naranja
            (36, "ENTREGADO",  "EFECTIVO",    [(1, 2), (4, 1)]),
            (34, "ENTREGADO",  "MERCADOPAGO", [(0, 1), (5, 2)]),
            (32, "ENTREGADO",  "MERCADOPAGO", [(2, 2)]),
            (30, "CANCELADO",  "MERCADOPAGO", [(3, 1)]),            # cancelado — no suma
            # ── Hace ~3 semanas ──────────────────────────────────────────────
            (28, "ENTREGADO",  "MERCADOPAGO", [(0, 1), (4, 1), (9, 2)]),  # + Agua x2
            (26, "ENTREGADO",  "EFECTIVO",    [(1, 1), (6, 1)]),
            (24, "ENTREGADO",  "MERCADOPAGO", [(2, 1), (7, 1)]),
            (22, "ENTREGADO",  "MERCADOPAGO", [(3, 2), (5, 1)]),
            (20, "ENTREGADO",  "EFECTIVO",    [(0, 1), (8, 1)]),
            # ── Hace ~1-2 semanas ────────────────────────────────────────────
            (18, "ENTREGADO",  "MERCADOPAGO", [(1, 1), (4, 2)]),
            (16, "ENTREGADO",  "EFECTIVO",    [(2, 1), (6, 1)]),
            (14, "ENTREGADO",  "MERCADOPAGO", [(0, 2), (9, 1)]),
            (12, "CANCELADO",  "EFECTIVO",    [(3, 1)]),            # cancelado — no suma
            (10, "ENTREGADO",  "MERCADOPAGO", [(1, 1), (5, 1), (7, 1)]),
            # ── Esta semana ──────────────────────────────────────────────────
            (7,  "ENTREGADO",  "EFECTIVO",    [(2, 2), (4, 1)]),
            (5,  "ENTREGADO",  "MERCADOPAGO", [(0, 1), (8, 2)]),
            (3,  "EN_PREP",    "MERCADOPAGO", [(1, 1), (6, 1)]),
            (2,  "CONFIRMADO", "EFECTIVO",    [(3, 1), (5, 1)]),
            (1,  "CONFIRMADO", "MERCADOPAGO", [(0, 2)]),
            (0,  "PENDIENTE",  "MERCADOPAGO", [(2, 1), (4, 1)]),
        ]

        # Mapa de transiciones de estado para construir el historial
        RUTA: dict[str, list[str]] = {
            "PENDIENTE":  [],
            "CONFIRMADO": ["CONFIRMADO"],
            "EN_PREP":    ["CONFIRMADO", "EN_PREP"],
            "ENTREGADO":  ["CONFIRMADO", "EN_PREP", "ENTREGADO"],
            "CANCELADO":  ["CANCELADO"],
        }

        creados = 0
        for dias_atras, estado_final, forma_pago, items_spec in PEDIDOS_DEMO:
            fecha_creacion = hoy - timedelta(days=dias_atras, hours=random.randint(8, 20))

            # Armar items con snapshots de precio
            items = []
            subtotal = Decimal("0.00")
            for prod_idx, cantidad in items_spec:
                if prod_idx >= len(productos):
                    continue
                prod = productos[prod_idx]
                precio = prod.precio_base
                sub    = precio * cantidad
                subtotal += sub
                items.append((prod, cantidad, precio, sub))

            if not items:
                continue

            total  = subtotal + COSTO_ENVIO
            codigo = generar_codigo(session, "pedido")

            pedido = Pedido(
                codigo=codigo,
                usuario_id=cliente.id,
                estado_codigo=estado_final,
                forma_pago_codigo=forma_pago,
                subtotal=subtotal,
                descuento=Decimal("0.00"),
                costo_envio=COSTO_ENVIO,
                total=total,
                created_at=fecha_creacion,
                updated_at=fecha_creacion,
            )
            session.add(pedido)
            session.flush()

            # DetallePedido (snapshots inmutables)
            for prod, cantidad, precio, sub in items:
                session.add(DetallePedido(
                    pedido_id=pedido.id,
                    producto_id=prod.id,
                    cantidad=cantidad,
                    nombre_snapshot=prod.nombre,
                    precio_snapshot=precio,
                    subtotal_snap=sub,
                    created_at=fecha_creacion,
                ))

            # HistorialEstadoPedido — primer registro (RN-02: estado_desde=None)
            t = fecha_creacion
            session.add(HistorialEstadoPedido(
                pedido_id=pedido.id,
                estado_desde=None,
                estado_hacia="PENDIENTE",
                usuario_id=cliente.id,
                created_at=t,
            ))

            # Transiciones posteriores según la ruta del estado final
            estado_prev = "PENDIENTE"
            for estado_sig in RUTA[estado_final]:
                t = t + timedelta(minutes=random.randint(10, 45))
                session.add(HistorialEstadoPedido(
                    pedido_id=pedido.id,
                    estado_desde=estado_prev,
                    estado_hacia=estado_sig,
                    usuario_id=admin.id,
                    created_at=t,
                ))
                estado_prev = estado_sig

            # Pago aprobado para pedidos MERCADOPAGO que llegaron al menos a CONFIRMADO
            if forma_pago == "MERCADOPAGO" and estado_final not in ("PENDIENTE", "CANCELADO"):
                t_pago = fecha_creacion + timedelta(minutes=random.randint(2, 8))
                session.add(Pago(
                    pedido_id=pedido.id,
                    monto=total,
                    transaction_amount=total,
                    estado="aprobado",
                    external_reference=str(uuid.uuid4()),
                    mp_payment_id=random.randint(100_000_000, 999_999_999),
                    mp_status="approved",
                    mp_status_detail="accredited",
                    payment_method_id="visa",
                    idempotency_key=str(uuid.uuid4()),
                    created_at=t_pago,
                    updated_at=t_pago + timedelta(seconds=30),
                ))

            creados += 1
            print(f"  ✓ {codigo} | {estado_final:10s} | {forma_pago:12s} | ${total:.2f}")

        session.commit()
        print(f"  {creados} pedidos demo sembrados.")


def seed():
    # Importar todos los modelos para que SQLModel los registre
    import app.modules.categorias.models    # noqa: F401
    import app.modules.ingredientes.models  # noqa: F401
    import app.modules.productos.models     # noqa: F401
    import app.modules.pedidos.models       # noqa: F401
    import app.modules.pagos.models         # noqa: F401
    from app.modules.ingredientes.models import UnidadMedida

    print("\n── FormaPago, EstadoPedido y UnidadMedida ─────────")
    with Session(engine) as session:
        for fp in FORMAS_PAGO:
            if not session.get(FormaPago, fp.codigo):
                session.add(fp)
                print(f"  ✓ FormaPago: {fp.codigo}")
            else:
                print(f"  · FormaPago ya existe: {fp.codigo}")

        for ep in ESTADOS_PEDIDO:
            if not session.get(EstadoPedido, ep.codigo):
                session.add(ep)
                print(f"  ✓ EstadoPedido: {ep.codigo}")
            else:
                print(f"  · EstadoPedido ya existe: {ep.codigo}")

        for codigo, nombre, simbolo, tipo in UNIDADES_MEDIDA:
            existe = session.exec(
                select(UnidadMedida).where(UnidadMedida.codigo == codigo)
            ).first()
            if not existe:
                session.add(UnidadMedida(codigo=codigo, nombre=nombre, simbolo=simbolo, tipo=tipo))
                print(f"  ✓ UnidadMedida: {codigo} ({simbolo})")
            else:
                print(f"  · UnidadMedida ya existe: {codigo}")

        session.commit()

    print("\n── Roles y Usuarios ──────────────────────────────")
    _seed_roles_y_usuarios()

    print("\n── Catálogo Fast Food ────────────────────────────")
    _seed_catalogo_fastfood()

    print("\n── Pedidos Demo ──────────────────────────────────")
    _seed_pedidos_demo()

    print("\n✅ Seed completado.")


if __name__ == "__main__":
    seed()
