// src/pages/LoginPage.tsx
import { useState } from 'react'
import { useNavigate, Navigate, Link, useLocation } from 'react-router-dom'
import { useAuth, useAuthStore } from '../store/authStore'
import type { RolCodigo } from '../models/auth'


/**
 * Destino post-login según rol:
 * - CLIENT puro → catálogo de la tienda.
 * - STOCK (sin ADMIN/PEDIDOS) → gestión de productos, que es su área de trabajo.
 * - ADMIN / PEDIDOS → gestión de pedidos.
 */
function destinoPorRol(roles: RolCodigo[]): string {
  const esClient = roles.length === 1 && roles.includes('CLIENT')
  if (esClient) return '/store'
  const esStockPuro =
    roles.includes('STOCK') && !roles.some(r => r === 'ADMIN' || r === 'PEDIDOS')
  if (esStockPuro) return '/productos'
  return '/pedidos'
}

export default function LoginPage() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Si el cliente fue mandado al login desde el carrito/checkout, volvemos ahí.
  const from = (location.state as { from?: string } | null)?.from ?? null

  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  if (user) return <Navigate to={from ?? destinoPorRol(user.roles)} replace />

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      const roles = (useAuthStore.getState().user?.roles ?? []) as RolCodigo[]
      navigate(from ?? destinoPorRol(roles))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al iniciar sesión')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-950 flex flex-col items-center justify-center px-4">
      <div className="text-center mb-8">
        <p className="text-5xl mb-3">🍴</p>
        <h1 className="text-3xl font-bold text-blue-700 dark:text-blue-400">Food Store</h1>
        <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Sistema de gestión</p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-md w-full max-w-sm p-8 flex flex-col gap-4"
      >
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
          autoComplete="email"
          className="border border-gray-300 dark:border-gray-600 rounded-xl px-5 py-3 focus:outline-none focus:ring-2 focus:ring-blue-400 text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 placeholder-gray-400 dark:placeholder-gray-500"
        />

        <input
          type="password"
          placeholder="Contraseña"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
          autoComplete="current-password"
          className="border border-gray-300 dark:border-gray-600 rounded-xl px-5 py-3 focus:outline-none focus:ring-2 focus:ring-blue-400 text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 placeholder-gray-400 dark:placeholder-gray-500"
        />

        {error && (
          <p className="text-sm text-red-500 text-center bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-xl transition disabled:opacity-50"
        >
          {loading ? 'Ingresando...' : 'Iniciar sesión'}
        </button>

        <div className="text-xs text-center text-gray-400 dark:text-gray-500 mt-1 space-y-0.5">
          <p><strong>admin@foodstore.com</strong> / admin123 — acceso total</p>
          <p><strong>stock@foodstore.com</strong> / stock123 — gestión de stock</p>
          <p><strong>pedidos@foodstore.com</strong> / pedidos123 — gestión de pedidos</p>
          <p><strong>cliente@foodstore.com</strong> / cliente123 — cliente</p>
        </div>

        <p className="text-sm text-center text-gray-500 dark:text-gray-400">
          ¿No tenés cuenta?{' '}
          <Link to="/register" className="text-blue-600 dark:text-blue-400 hover:underline font-medium">
            Registrate
          </Link>
        </p>
      </form>
    </div>
  )
}
