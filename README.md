# 🍔 Food Store
## Sistema de Gestión de Pedidos de Comida

TPI Programación 4 - Tecnicatura Universitaria en Programación - UTN FRM

Grupo: Bits&Bytes

Integrantes: 
  - Marín, Agustín
  - Muñoz, Carlos
  - Raia, Sofia
  - Rolón, Octavio

Link al video: 

Aplicación web full-stack para la gestión de pedidos de comida: catálogo con imágenes (Cloudinary), carrito, pedidos con máquina de estados (FSM) y trazabilidad append-only, pagos con MercadoPago Checkout Pro, y actualizaciones de estado en tiempo real por WebSocket.

**Stack:** FastAPI + SQLModel + PostgreSQL + Alembic (backend) · React + TypeScript + Vite + Zustand + TanStack Query (frontend).

---

## Tabla de contenidos

1. [Requisitos previos](#1-requisitos-previos)
2. [Estructura del repo](#2-estructura-del-repo)
3. [Base de datos (PostgreSQL)](#3-base-de-datos-postgresql)
4. [Backend — setup desde cero](#4-backend--setup-desde-cero)
5. [Frontend — setup desde cero](#5-frontend--setup-desde-cero)
6. [Usuarios de prueba (seed)](#6-usuarios-de-prueba-seed)
7. [Configurar MercadoPago](#7-configurar-mercadopago)
8. [Configurar Cloudinary](#8-configurar-cloudinary)
9. [Tests desde cero](#9-tests-desde-cero)
10. [Variables de entorno](#10-variables-de-entorno)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Requisitos previos

| Herramienta | Versión | Para qué |
|---|---|---|
| Python | 3.11+ (probado en 3.13) | backend |
| Node.js | 18+ | frontend |
| PostgreSQL | 15+ (o Docker) | base de datos |
| ngrok | última | exponer el webhook de MercadoPago (opcional) |

Cuenta gratuita de [MercadoPago Developers](https://www.mercadopago.com.ar/developers) y de [Cloudinary](https://cloudinary.com) si querés probar pagos e imágenes.

---

## 2. Estructura del repo

```
foodstore/
├── backend/
│   ├── app/
│   │   ├── core/          # config, uow, repository base, rate limit, websocket, exceptions
│   │   └── modules/       # auth, usuarios, productos, pedidos, pagos, uploads, admin, ...
│   ├── alembic/           # migraciones
│   ├── tests/             # pytest (integration + unit)
│   ├── seed.py            # datos iniciales
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/               # pages, features, components, hooks, store, api, models
    ├── package.json
    └── .env.example
```

---

## 3. Base de datos (PostgreSQL)

Necesitás un PostgreSQL escuchando en el puerto **5433** (el que usa `.env.example`). La forma más rápida es Docker:

```bash
docker run -d --name foodstore_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=food_store_db \
  -p 5433:5432 \
  postgres:15
```

> Si ya tenés un PostgreSQL local en el puerto 5432, podés usarlo: ajustá `postgres_host`, `postgres_port`, `postgres_user` y `postgres_password` en el `.env` del backend (ver [§10](#10-variables-de-entorno)) y creá la base `food_store_db`.

Verificar que levantó:

```bash
docker exec -it foodstore_db psql -U postgres -d food_store_db -c "SELECT 1;"
```

---

## 4. Backend — setup desde cero

Desde la carpeta `backend/`:

```bash
cd backend

# 1) Entorno virtual
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# 2) Dependencias
pip install -r requirements.txt

# 3) Variables de entorno
cp .env.example .env        # Windows: copy .env.example .env
#   → editá .env y poné, como mínimo, un SECRET_KEY propio:
#     openssl rand -hex 32

# 4) Crear las tablas (migraciones)
alembic upgrade head

# 5) Cargar datos iniciales (roles, estados, formas de pago, unidades, usuarios)
python seed.py

# 6) Levantar la API
uvicorn app.main:app --reload
```

La API queda en **http://localhost:8000**.
Documentación interactiva: **http://localhost:8000/docs** (Swagger) y **/redoc**.

> El orden importa: `alembic upgrade head` **antes** de `python seed.py`. Alembic crea el esquema y el seed inserta los datos.

---

## 5. Frontend — setup desde cero

Desde la carpeta `frontend/` (en otra terminal, con el backend ya corriendo):

```bash
cd frontend

# 1) Dependencias (el repo usa npm; el lockfile es package-lock.json)
npm install

# 2) Variables de entorno
cp .env.example .env        # Windows: copy .env.example .env
#   VITE_API_URL apunta al backend (http://localhost:8000)
#   VITE_MP_PUBLIC_KEY: dejala vacía si todavía no configuraste MercadoPago

# 3) Levantar el dev server
npm run dev
```

El frontend queda en **http://localhost:5174**.

Build de producción: `npm run build` (genera `dist/`).

---

## 6. Usuarios de prueba (seed)

`seed.py` crea cuatro usuarios, uno por rol:

| Rol | Email | Password |
|---|---|---|
| ADMIN | `admin@foodstore.com` | `admin123` |
| STOCK | `stock@foodstore.com` | `stock123` |
| PEDIDOS | `pedidos@foodstore.com` | `pedidos123` |
| CLIENT | `cliente@foodstore.com` | `cliente123` |

> Son credenciales de desarrollo. Cambialas antes de cualquier despliegue real.

---

## 7. Configurar MercadoPago

El pago usa **Checkout Pro** con confirmación por webhook (IPN). Para probarlo end-to-end:

### 7.1 Obtener credenciales de prueba
1. Entrá a [MercadoPago Developers](https://www.mercadopago.com.ar/developers) → tus integraciones → creá una aplicación.
2. En **Credenciales de prueba** copiá el **Access Token** y la **Public Key**.

### 7.2 Exponer el webhook con ngrok
MercadoPago necesita una URL pública para notificar el resultado del pago. En local se usa ngrok:

```bash
ngrok http 8000
```

Copiá la URL `https://<algo>.ngrok-free.app` que te da.

### 7.3 Completar el `.env` del backend
```env
MP_ACCESS_TOKEN=
MP_PUBLIC_KEY=
NGROK_URL=https://<algo>.ngrok-free.app
MP_WEBHOOK_URL=https://<algo>.ngrok-free.app/api/v1/pagos/webhook
FRONTEND_URL=http://localhost:5174
```

### 7.4 Completar el `.env` del frontend
```env
VITE_MP_PUBLIC_KEY=
```
(Si `VITE_MP_PUBLIC_KEY` queda vacía, el botón de pago se deshabilita y el resto de la app funciona igual.)

Reiniciá backend y frontend para que tomen las variables.

### 7.5 Tarjetas de prueba
Usá las [tarjetas de test de MercadoPago](https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/additional-content/your-integrations/test/cards). Para aprobar un pago, en el nombre del titular poné **APRO**.

---

## 8. Configurar Cloudinary

Para subir imágenes de productos/categorías desde el panel admin:

1. Creá una cuenta en [Cloudinary](https://cloudinary.com) y entrá al Dashboard.
2. Copiá **Cloud name**, **API Key** y **API Secret**.
3. Completá el `.env` del backend:

```env
CLOUDINARY_CLOUD_NAME=tu-cloud-name
CLOUDINARY_API_KEY=tu-api-key
CLOUDINARY_API_SECRET=tu-api-secret
CLOUDINARY_FOLDER=foodstore
```

El `API_SECRET` vive **solo en el backend** y nunca se expone al frontend (el upload es signed desde el server).

---

## 9. Tests desde cero

Los tests de integración corren contra una **base de datos de test dedicada** (nunca tocan `food_store_db`).

```bash
cd backend
source .venv/bin/activate          # si no está activo

# 1) Crear la base de test (una sola vez)
docker exec -it foodstore_db createdb -U postgres food_store_test_db

# 2) Indicar la URL de la base de test (ajustá usuario/clave a tu Postgres)
#    Linux/macOS:
export TEST_DATABASE_URL="postgresql://postgres:password@localhost:5432/food_store_test_db"
#    Windows (PowerShell):
#    $env:TEST_DATABASE_URL="postgresql://postgres:password@localhost:5432/food_store_test_db"

# 3) Correr la suite
pytest                  # todos
pytest -m integration   # solo integración
pytest -m unit          # solo unitarios
pytest tests/integration/test_pedidos.py -v   # un archivo puntual
```

No hace falta correr `alembic` ni `seed` para los tests: el `conftest.py` crea las tablas, limpia la base y siembra el catálogo y los usuarios de test automáticamente antes de cada test.

### Cobertura (opcional)
```bash
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

---

## 10. Variables de entorno

### Backend (`backend/.env`)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `postgres_user` / `postgres_password` | credenciales de PostgreSQL | `postgres` / `password` |
| `postgres_db` / `postgres_host` / `postgres_port` | base, host y puerto | `food_store_db` / `localhost` / `5432` |
| `SECRET_KEY` | clave para firmar JWT (mín. 32 chars) | `openssl rand -hex 32` |
| `ALGORITHM` | algoritmo JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | expiración del access token | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | expiración del refresh token | `7` |
| `ENV` | `development` / `production` / `test` | `development` |
| `RATE_LIMIT_AUTH_PER_MINUTE` | recarga de cupo de auth por minuto | `10` |
| `RATE_LIMIT_AUTH_BURST` | intentos fallidos tolerados antes del bloqueo | `5` |
| `RATE_LIMIT_AUTH_LOCKOUT_SECONDS` | duración del bloqueo tras agotar el cupo (seg.) | `900` |
| `MP_ACCESS_TOKEN` / `MP_PUBLIC_KEY` | credenciales TEST de MercadoPago | `APP_USR-` |
| `NGROK_URL` / `MP_WEBHOOK_URL` | URL pública y endpoint del webhook | `https://...ngrok-free.app` |
| `FRONTEND_URL` | redirect tras el checkout | `http://localhost:5174` |
| `CLOUDINARY_CLOUD_NAME` / `_API_KEY` / `_API_SECRET` | credenciales Cloudinary | — |
| `CLOUDINARY_FOLDER` | carpeta destino en Cloudinary | `foodstore` |

> **Seguridad del login:** con la config por defecto, **5 logins fallidos seguidos** desde una misma IP bloquean el login por `RATE_LIMIT_AUTH_LOCKOUT_SECONDS` (15 min). Los logins exitosos no consumen cupo. Ajustá `RATE_LIMIT_AUTH_BURST` (cantidad de fallos) y `RATE_LIMIT_AUTH_LOCKOUT_SECONDS` (duración del bloqueo) a gusto.

### Frontend (`frontend/.env`)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `VITE_API_URL` | URL base del backend | `http://localhost:8000` |
| `VITE_MP_PUBLIC_KEY` | public key TEST de MercadoPago (vacía = pago deshabilitado) | `TEST-...` |

---

## 11. Troubleshooting

| Síntoma | Causa probable / solución |
|---|---|
| `connection refused` al arrancar el backend | PostgreSQL no está levantado o el puerto/credenciales del `.env` no coinciden. |
| `relation "..." does not exist` | Falta correr `alembic upgrade head`. |
| Login siempre falla aunque la clave sea correcta | ¿Corriste `python seed.py` después de las migraciones? |
| `429 Too Many Requests` en el login | Se activó el bloqueo por intentos fallidos. Esperá el lockout o reiniciá el backend (resetea los contadores en memoria). |
| El botón de pago no aparece | Falta `VITE_MP_PUBLIC_KEY` en el `.env` del frontend. |
| MercadoPago no confirma el pago | ngrok caído o `MP_WEBHOOK_URL` desactualizada (cambia en cada reinicio de ngrok). |
| Tests fallan con error de conexión | Falta crear `food_store_test_db` o exportar `TEST_DATABASE_URL` con las credenciales correctas. |
