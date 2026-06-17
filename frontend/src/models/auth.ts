// src/models/auth.ts

export type RolCodigo = 'ADMIN' | 'STOCK' | 'PEDIDOS' | 'CLIENT'

/**
 * Estado del usuario autenticado que el frontend necesita para la UI.
 * Los tokens NO viven aquí: el browser los maneja en cookies HttpOnly,
 * inaccesibles desde JavaScript.
 */
export interface AuthUser {
  id:       number
  email:    string
  nombre:   string
  apellido: string
  roles:    RolCodigo[]
}

// ── Helpers de rol ────────────────────────────────────────────────────────────

/** Devuelve true si el usuario tiene el rol indicado. */
export function hasRole(user: AuthUser | null, rol: RolCodigo): boolean {
  return user?.roles.includes(rol) ?? false
}

/**
 * Helper T-B23: devuelve true si el usuario tiene AL MENOS uno de los roles.
 *
 * @example
 *   hasAnyRole(user, ['ADMIN', 'STOCK'])  // → true si user es ADMIN o STOCK
 */
export function hasAnyRole(user: AuthUser | null, roles: RolCodigo[]): boolean {
  if (!user) return false
  return roles.some(r => user.roles.includes(r))
}

/** Atajo: devuelve true si el usuario es ADMIN. */
export function isAdmin(user: AuthUser | null): boolean {
  return hasRole(user, 'ADMIN')
}
