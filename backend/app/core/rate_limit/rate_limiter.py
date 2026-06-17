# app/core/rate_limit/rate_limiter.py
"""
Rate limiting en memoria con algoritmo Token Bucket.

Dos modos de uso:

1. Genérico (check/consume): cada request consume un token. Útil para limitar
   tráfico general por IP.

2. Por intentos fallidos (is_blocked/register_failure): el bucket NO se consume
   en cada request; sólo se descuenta un token cuando el intento FALLA. Al agotar
   el bucket de fallos se activa un bloqueo fijo y configurable (lockout). Esto es
   lo que usa auth: un login exitoso no gasta cupo; sólo los fallidos cuentan, y
   tras N fallos seguidos la IP queda bloqueada por `lockout_seconds`.

Todo es thread-safe con threading.Lock.
"""
import threading
import time


class TokenBucket:
    """
    Token Bucket thread-safe.

    Args:
        capacity:        Número máximo de tokens (= tamaño del burst).
        refill_rate:     Tokens que se recargan por segundo.
        lockout_seconds: Si > 0, al agotar el bucket por fallos se bloquea por
                         esta ventana fija (no se recarga hasta que expire).
    """

    def __init__(self, capacity: float, refill_rate: float, lockout_seconds: float = 0.0) -> None:
        self._capacity = capacity
        self._tokens = float(capacity)  # arranca lleno
        self._refill_rate = refill_rate  # tokens/segundo
        self._lockout_seconds = lockout_seconds
        self._locked_until = 0.0  # monotonic time hasta el cual está bloqueado
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self, now: float) -> None:
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    def consume(self, tokens: int = 1) -> tuple[bool, float]:
        """
        Modo genérico: intenta consumir `tokens`.
        Returns (True, 0.0) si hay suficientes; (False, retry_after) si no.
        """
        with self._lock:
            now = time.monotonic()
            self._refill(now)
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True, 0.0
            retry_after = (tokens - self._tokens) / self._refill_rate
            return False, retry_after

    # ── Modo por intentos fallidos ────────────────────────────────────────────

    def peek_blocked(self) -> tuple[bool, float]:
        """
        Consulta SIN consumir si la clave está en lockout activo.
        Si el lockout ya expiró, rehabilita el bucket (lleno) y devuelve no-bloqueado.
        Returns (bloqueado, retry_after_segundos).
        """
        with self._lock:
            now = time.monotonic()
            if self._locked_until > now:
                return True, self._locked_until - now
            # Lockout expirado: reset del bucket de fallos.
            if self._locked_until != 0.0:
                self._tokens = float(self._capacity)
                self._locked_until = 0.0
                self._last_refill = now
            return False, 0.0

    def register_failure(self) -> None:
        """
        Registra un intento fallido: consume 1 token de fallo y, si con eso se
        agota el bucket, activa el lockout fijo.
        """
        with self._lock:
            now = time.monotonic()
            self._refill(now)
            if self._tokens >= 1:
                self._tokens -= 1
            if self._tokens < 1 and self._lockout_seconds > 0:
                self._locked_until = now + self._lockout_seconds


class RateLimiter:
    """
    Administrador de buckets por clave de cliente (típicamente la IP).

    Args:
        per_minute:      Tasa de recarga en tokens por minuto.
        burst:           Capacidad máxima (tamaño del burst / cantidad de fallos
                         tolerados antes del bloqueo).
        lockout_seconds: Ventana de bloqueo fija al agotar el bucket de fallos.
    """

    def __init__(self, per_minute: float, burst: int, lockout_seconds: float = 0.0) -> None:
        self._per_minute = per_minute
        self._burst = burst
        self._lockout_seconds = lockout_seconds
        self._refill_rate = per_minute / 60.0  # tokens/segundo
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def _get_bucket(self, key: str) -> TokenBucket:
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket(
                    capacity=self._burst,
                    refill_rate=self._refill_rate,
                    lockout_seconds=self._lockout_seconds,
                )
            return self._buckets[key]

    # ── Modo genérico ─────────────────────────────────────────────────────────

    def check(self, key: str) -> tuple[bool, float]:
        """Consume un token por request. Returns (allowed, retry_after_seconds)."""
        return self._get_bucket(key).consume()

    # ── Modo por intentos fallidos ────────────────────────────────────────────

    def is_blocked(self, key: str) -> tuple[bool, float]:
        """Consulta sin consumir si la clave está bloqueada por fallos previos."""
        return self._get_bucket(key).peek_blocked()

    def register_failure(self, key: str) -> None:
        """Registra un intento fallido para la clave (consume token de fallo)."""
        self._get_bucket(key).register_failure()

    def reset(self) -> None:
        """Elimina todos los buckets. Usado en tests para limpiar el estado."""
        with self._lock:
            self._buckets.clear()