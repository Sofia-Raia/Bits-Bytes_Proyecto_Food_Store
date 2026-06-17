// src/routes/PrivateRoute.tsx
import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../store/authStore'
import type { RolCodigo } from '../models/auth'

interface Props {
  children: ReactNode
  /** Lista de roles permitidos. Si se omite, solo requiere estar autenticado. */
  roles?: RolCodigo[]
}

/**
 * Guard de ruta autenticada.
 * - Sin user → redirige a /login.
 * - Con roles definidos: si el user no tiene ninguno → redirige a /.
 */
export default function PrivateRoute({ children, roles }: Props) {
  const { user } = useAuth()

  if (!user) return <Navigate to="/login" replace />

  if (roles && !roles.some(r => user.roles.includes(r))) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
