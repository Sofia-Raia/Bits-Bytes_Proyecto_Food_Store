# app/modules/auth/repository.py
from datetime import datetime, timezone
from typing import Optional, List

from sqlmodel import Session, select

from app.core.repository import BaseRepository
from app.modules.auth.models import Usuario, UsuarioRol, RefreshToken


class AuthRepository(BaseRepository[Usuario]):
    """
    Repositorio del módulo auth.
    Solo lectura: autenticación y carga de roles.
    Las mutaciones de Usuario viven en UsuarioRepository.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session, Usuario)

    def get_by_email(self, email: str) -> Optional[Usuario]:
        """Usuario por email, independientemente de si está activo."""
        return self.session.exec(
            select(Usuario).where(Usuario.email == email)
        ).first()

    def get_active_by_email(self, email: str) -> Optional[Usuario]:
        """Usuario por email solo si no fue eliminado lógicamente."""
        return self.session.exec(
            select(Usuario).where(
                Usuario.email == email,
                Usuario.deleted_at == None,  # noqa: E711
            )
        ).first()

    def get_roles(self, usuario_id: int) -> List[str]:
        """Códigos de rol activos (sin expirar) del usuario."""
        now = datetime.now(timezone.utc)
        rows = self.session.exec(
            select(UsuarioRol).where(
                UsuarioRol.usuario_id == usuario_id,
                (UsuarioRol.expires_at == None) | (UsuarioRol.expires_at > now),  # noqa: E711
            )
        ).all()
        return [r.rol_codigo for r in rows]

    # ── Refresh tokens (revocación de sesión) ─────────────────────────────────

    def add_refresh_token(self, usuario_id: int, jti: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(usuario_id=usuario_id, jti=jti, expires_at=expires_at)
        self.session.add(token)
        self.session.flush()
        return token

    def get_refresh_token(self, jti: str) -> Optional[RefreshToken]:
        return self.session.exec(
            select(RefreshToken).where(RefreshToken.jti == jti)
        ).first()

    def revoke_refresh_token(self, jti: str) -> None:
        """Marca un refresh token como revocado (idempotente)."""
        token = self.get_refresh_token(jti)
        if token and token.revoked_at is None:
            token.revoked_at = datetime.now(timezone.utc)
            self.session.add(token)

    def revoke_all_for_user(self, usuario_id: int) -> int:
        """Revoca todos los refresh tokens activos del usuario. Devuelve cuántos revocó."""
        ahora = datetime.now(timezone.utc)
        tokens = self.session.exec(
            select(RefreshToken).where(
                RefreshToken.usuario_id == usuario_id,
                RefreshToken.revoked_at == None,  # noqa: E711
            )
        ).all()
        for t in tokens:
            t.revoked_at = ahora
            self.session.add(t)
        return len(tokens)
