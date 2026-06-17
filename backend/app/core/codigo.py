# app/core/codigo.py
"""
Generador de códigos únicos por entidad.

Patrón:    {PREFIJO}-{NNNN}
Padding:   4 dígitos con ceros a la izquierda
Separador: guión medio (-)
Ejemplo:   INGR-0001, CAT-0042, PROD-0100, PED-0001

Inmutabilidad: el código se asigna al crear y nunca se modifica.

─── Registro de prefijos activos ───────────────────────────────────────────────
  INGR  → Ingrediente     (tabla: ingredientes)
  CAT   → Categoria       (tabla: categorias)
  PROD  → Producto        (tabla: productos)
  PED   → Pedido          (tabla: pedidos)

─── Para agregar una nueva entidad ─────────────────────────────────────────────
  1. Agregar entrada en PREFIJOS  con clave = nombre singular de la entidad
  2. Agregar entrada en TABLAS    con clave = mismo nombre, valor = nombre de tabla
  3. Llamar a generar_codigo(session, "nombre_entidad") en el service.create()
  4. Documentar el nuevo prefijo en este docstring

─── Thread-safety ───────────────────────────────────────────────────────────────
  Se usa MAX sobre el campo numérico para evitar gaps por borrados lógicos.
  La unicidad final está garantizada por el constraint UNIQUE en la columna.
  En caso de colisión concurrente, la DB lanzará IntegrityError.
"""
from sqlalchemy import text
from sqlmodel import Session

PREFIJOS: dict[str, str] = {
    "ingrediente": "INGR",
    "categoria":   "CAT",
    "producto":    "PROD",
    "pedido":      "PED",
}

TABLAS: dict[str, str] = {
    "ingrediente": "ingredientes",
    "categoria":   "categorias",
    "producto":    "productos",
    "pedido":      "pedidos",
}


def generar_codigo(session: Session, entidad: str) -> str:
    """
    Genera el próximo código disponible para la entidad dada.
    Extrae el número máximo existente vía SQL y le suma 1.
    Si no hay registros previos, arranca desde 0001.
    """
    prefijo = PREFIJOS[entidad]
    tabla   = TABLAS[entidad]

    row = session.execute(
        text(
            f"SELECT MAX(CAST(SPLIT_PART(codigo, '-', 2) AS INTEGER)) "
            f"FROM {tabla} "
            f"WHERE codigo LIKE :patron"
        ),
        {"patron": f"{prefijo}-%"},
    ).scalar()

    nuevo_num = (row or 0) + 1
    return f"{prefijo}-{nuevo_num:04d}"
