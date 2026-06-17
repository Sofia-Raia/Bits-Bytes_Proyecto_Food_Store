# app/modules/auth/security.py
"""
Primitivas de seguridad SIN acceso a base de datos.

Aquí vive exclusivamente la generación/validación de credenciales:
- Hashing y verificación de passwords (bcrypt).
- Emisión y decodificación de JWT (access / refresh).

Se separa de service.py a propósito: la generación de tokens no debe convivir
con la persistencia del usuario. Estas funciones son puras (no tocan la sesión)
y por eso son trivialmente testeables y reutilizables.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.core.config import settings


# ── Passwords ─────────────────────────────────────────────────────────────────

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode["type"] = "access"
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict, jti: str) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode["type"] = "refresh"
    to_encode["jti"] = jti
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica y valida firma + expiración. Lanza JWTError si falla."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])