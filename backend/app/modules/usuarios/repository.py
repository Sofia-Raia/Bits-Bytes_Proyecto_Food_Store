# app/modules/usuarios/repository.py
from datetime import datetime, timezone
from typing import Optional, List

from sqlmodel import Session, select, func, asc, desc

from app.core.repository import BaseRepository
from app.modules.usuarios.models import Rol, Usuario, UsuarioRol

_SORT_COLUMNS = {
    'nombre':     Usuario.nombre,
    'apellido':   Usuario.apellido,
    'email':      Usuario.email,
    'created_at': Usuario.created_at,
}


class UsuarioRepository(BaseRepository[Usuario]):

    def __init__(self, session: Session) -> None:
        super().__init__(session, Usuario)

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_by_email(self, email: str) -> Optional[Usuario]:
        return self.session.exec(
            select(Usuario).where(Usuario.email == email)
        ).first()

    def get_all_paginado(
        self,
        offset: int = 0,
        limit: int = 20,
        incluir_inactivos: bool = False,
        nombre: Optional[str] = None,
        sort_by: str = 'nombre',
        sort_dir: str = 'asc',
    ) -> List[Usuario]:
        q = select(Usuario)
        if not incluir_inactivos:
            q = q.where(Usuario.deleted_at == None)  
        if nombre:
            q = q.where(
                (Usuario.nombre.ilike(f"%{nombre}%"))
                | (Usuario.apellido.ilike(f"%{nombre}%"))
                | (Usuario.email.ilike(f"%{nombre}%"))
            )
        col = _SORT_COLUMNS.get(sort_by, Usuario.nombre)
        order = asc(col) if sort_dir == 'asc' else desc(col)
        q = q.order_by(order).offset(offset).limit(limit)
        return list(self.session.exec(q).all())

    def count(
        self,
        incluir_inactivos: bool = False,
        nombre: Optional[str] = None,
    ) -> int:
        q = select(func.count(Usuario.id))
        if not incluir_inactivos:
            q = q.where(Usuario.deleted_at == None)  
        if nombre:
            q = q.where(
                (Usuario.nombre.ilike(f"%{nombre}%"))
                | (Usuario.apellido.ilike(f"%{nombre}%"))
                | (Usuario.email.ilike(f"%{nombre}%"))
            )
        return self.session.exec(q).one()

    def get_roles(self, usuario_id: int) -> List[str]:
        """Devuelve los códigos de rol activos (sin expirar) del usuario."""
        now = datetime.now(timezone.utc)
        rows = self.session.exec(
            select(UsuarioRol).where(
                UsuarioRol.usuario_id == usuario_id,
                (UsuarioRol.expires_at == None) | (UsuarioRol.expires_at > now),  
            )
        ).all()
        return [r.rol_codigo for r in rows]

    def rol_existe(self, codigo: str) -> bool:
        return self.session.get(Rol, codigo) is not None

    def count_admins_activos(self) -> int:
        """
        Cuenta cuántos usuarios ACTIVOS tienen el rol ADMIN asignado.
        Usado para prevenir que el sistema se quede sin ningún ADMIN.
        """
        now = datetime.now(timezone.utc)
        subq = (
            select(UsuarioRol.usuario_id)
            .where(
                UsuarioRol.rol_codigo == "ADMIN",
                (UsuarioRol.expires_at == None) | (UsuarioRol.expires_at > now),  
            )
        )
        q = select(func.count(Usuario.id)).where(
            Usuario.id.in_(subq),
            Usuario.deleted_at == None,  
        )
        return self.session.exec(q).one()

    # ── Mutaciones ─────────────────────────────────────────────────────────────

    def set_roles(
        self,
        usuario_id: int,
        nuevos_roles: List[str],
        admin_id: int,
    ) -> None:
        """Reemplaza todos los roles actuales por la nueva lista."""
        for ur in self.session.exec(
            select(UsuarioRol).where(UsuarioRol.usuario_id == usuario_id)
        ).all():
            self.session.delete(ur)
        self.session.flush()
        for codigo in nuevos_roles:
            self.session.add(UsuarioRol(
                usuario_id=usuario_id,
                rol_codigo=codigo,
                asignado_por_id=admin_id,
            ))
        self.session.flush()
