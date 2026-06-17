# app/core/config.py
import sys
from decimal import Decimal

from pydantic import computed_field
from pydantic_settings import BaseSettings

_DEFAULT_SECRET = "CHANGE_ME_IN_PROD_use_openssl_rand_hex_32"


class Settings(BaseSettings):
    postgres_user: str = "postgres"
    postgres_password: str = "password"
    postgres_db: str = "food_store_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5433

    # JWT
    SECRET_KEY: str = _DEFAULT_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30    # 30 minutos (access token)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7       # 7 días  (refresh token)

    # Entorno
    ENV: str = "development"  # "production" activa validaciones estrictas

    # Logging
    LOG_LEVEL: str = "INFO"

    # Rate limiting — valores por defecto (sobreescribibles en .env)
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 120  # requests/minuto por IP (general)
    RATE_LIMIT_DEFAULT_BURST: int = 20        # burst máximo (ventana corta)
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10      # requests/minuto por IP (auth endpoints)
    RATE_LIMIT_AUTH_BURST: int = 5            # burst máximo (auth endpoints)
    RATE_LIMIT_AUTH_LOCKOUT_SECONDS: int = 900     # bloqueo fijo tras superar el burst de auth (15 min)          

    # MercadoPago — credenciales TEST + URLs públicas (ngrok)
    MP_ACCESS_TOKEN: str = ""                 # access token TEST de MercadoPago
    MP_PUBLIC_KEY: str = ""                   # public key TEST
    MP_WEBHOOK_URL: str = ""                  # https://<ngrok>/api/v1/pagos/webhook
    NGROK_URL: str = ""                       # https://<sub>.ngrok-free.app (base de back_urls)
    FRONTEND_URL: str = "http://localhost:5174"  # destino del redirect tras el checkout

    # Cloudinary — upload firmado de imágenes (productos y categorías)
    CLOUDINARY_CLOUD_NAME: str = ""           # nombre de la cuenta (cloud name)
    CLOUDINARY_API_KEY: str = ""              # API key
    CLOUDINARY_API_SECRET: str = ""           # API secret (NUNCA se expone al frontend)
    CLOUDINARY_FOLDER: str = "foodstore"      # carpeta destino dentro de Cloudinary

    # Pedidos — costo de envío fijo (v1). Fuente de verdad única del cargo:
    # lo aplica el backend al total del pedido (lo que MercadoPago cobra) y lo
    # consume el frontend en el checkout vía GET /pedidos/config para mostrar
    # exactamente el mismo monto. Override por env: COSTO_ENVIO.
    COSTO_ENVIO: Decimal = Decimal("5000.00")

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

# ── Guard producción ──────────────────────────────────────────────────────────
if settings.ENV == "production" and settings.SECRET_KEY == _DEFAULT_SECRET:
    print(
        "ERROR: SECRET_KEY no configurada. "
        "Definí SECRET_KEY en el entorno antes de iniciar en producción.",
        file=sys.stderr,
    )
    sys.exit(1)
