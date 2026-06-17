// src/components/Navbar.tsx
import { useState, useRef, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../store/authStore'
import { hasAnyRole } from '../models/auth'
import { useTheme } from '../store/uiStore'
import { useCarrito } from '../store/carritoStore'

interface NavLink { to: string; label: string }

export default function Navbar() {
  const [menuAbierto, setMenuAbierto] = useState(false)
  const { pathname } = useLocation()
  const navigate     = useNavigate()
  const { user, logout } = useAuth()
  const menuRef      = useRef<HTMLDivElement>(null)
  const { dark, toggleTheme } = useTheme()
  const { totalItems } = useCarrito()

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuAbierto(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleLogout = async () => {
    setMenuAbierto(false)
    await logout()
    navigate('/login')
  }

  const esAdmin   = hasAnyRole(user, ['ADMIN'])
  const esStock   = hasAnyRole(user, ['STOCK'])
  const esPedidos = hasAnyRole(user, ['PEDIDOS'])
  const esClient  = hasAnyRole(user, ['CLIENT'])
  const esStaff   = esAdmin || esStock || esPedidos

  const links: NavLink[] = []

  links.push({ to: '/store', label: '🛍️ Tienda' })
  links.push({
    to: '/store/carrito',
    label: totalItems > 0 ? `🛒 Carrito (${totalItems})` : '🛒 Carrito',
  })

  if (user) {
    if (esStaff) {
      links.push({ to: '/pedidos', label: '📋 Pedidos' })
      if (esAdmin) {
        links.push({ to: '/estadisticas', label: '📊 Estadísticas' })
      }
      if (esAdmin || esStock) {
        links.push({ to: '/categorias',   label: '📂 Categorías' })
        links.push({ to: '/ingredientes', label: '🧂 Ingredientes' })
        links.push({ to: '/productos',    label: '🍽️ Productos' })
      }
      if (esAdmin || esStock) {
        links.push({ to: '/productos/aplicar-margen', label: '📊 Aplicar Margen' })
      }
      if (esAdmin) {
        links.push({ to: '/usuarios',    label: '👥 Usuarios' })
        links.push({ to: '/direcciones', label: '📍 Direcciones' })
      }
    } else if (esClient) {
      links.push({ to: '/productos',   label: '🍽️ Productos' })
      links.push({ to: '/store/mis-pedidos', label: '📋 Mis Pedidos' })
      links.push({ to: '/direcciones', label: '📍 Mis Direcciones' })
    }
  } else {
    links.push({ to: '/login', label: 'Iniciar sesión' })
  }

  const esActivo = (to: string) => {
    if (to === '/productos') return pathname === '/productos'
    return pathname.startsWith(to)
  }

  const roles    = user?.roles ?? []
  const rolBadge = esAdmin
    ? 'bg-yellow-400 text-yellow-900'
    : esPedidos
    ? 'bg-green-500 text-white'
    : esStock
    ? 'bg-purple-500 text-white'
    : 'bg-blue-500 text-white'

  return (
    <nav className="bg-blue-700 dark:bg-gray-900 text-white shadow-lg relative z-50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">

        {/* Logo */}
        <Link
          to="/pedidos"
          className="font-bold text-xl tracking-tight hover:text-blue-200 transition flex items-center gap-2"
        >
          🍴 Food Store
        </Link>

        {/* Nombre de usuario (desktop) */}
        {user && (
          <span className="hidden md:flex items-center gap-2 text-sm text-blue-200 font-medium">
            👤 {user.nombre}
            <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${rolBadge}`}>
              {roles.join(', ') || 'Sin rol'}
            </span>
          </span>
        )}

        {/* Menú hamburguesa */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuAbierto(prev => !prev)}
            aria-label="Abrir menú"
            aria-expanded={menuAbierto}
            className="p-2 rounded-lg hover:bg-blue-600 dark:hover:bg-gray-700 transition focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            {menuAbierto ? (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>

          {/* Dropdown */}
          {menuAbierto && (
            <div className="absolute right-0 top-full mt-2 w-64 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-100 dark:border-gray-700 py-2 z-[100]">

              {/* Info usuario */}
              {user && (
                <div className="px-4 py-2 border-b border-gray-100 dark:border-gray-700 mb-1">
                  <p className="text-xs text-gray-400 dark:text-gray-500">Sesión iniciada como</p>
                  <p className="text-sm font-bold text-gray-700 dark:text-gray-200">{user.nombre} {user.apellido}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{user.email}</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {roles.map(r => (
                      <span
                        key={r}
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          r === 'ADMIN'   ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' :
                          r === 'PEDIDOS' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'    :
                          r === 'STOCK'   ? 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300':
                          'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                        }`}
                      >
                        {r}
                      </span>
                    ))}
                    {roles.length === 0 && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">Sin rol</span>
                    )}
                  </div>
                </div>
              )}

              {/* Links de navegación */}
              <ul className="flex flex-col">
                {links.map(l => (
                  <li key={l.to}>
                    <Link
                      to={l.to}
                      onClick={() => setMenuAbierto(false)}
                      className={`block px-4 py-2.5 text-sm transition rounded-lg mx-1 ${
                        esActivo(l.to)
                          ? 'bg-blue-600 text-white font-semibold'
                          : 'text-gray-700 dark:text-gray-200 hover:bg-blue-50 dark:hover:bg-gray-700 hover:text-blue-700 dark:hover:text-blue-300'
                      }`}
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}

                {/* Tema */}
                <li className="border-t border-gray-100 dark:border-gray-700 mt-1 pt-1">
                  <button
                    onClick={toggleTheme}
                    className="w-full text-left px-4 py-2.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition rounded-lg"
                  >
                    {dark ? '☀️ Modo claro' : '🌙 Modo oscuro'}
                  </button>
                </li>

                {/* Cerrar sesión */}
                {user && (
                  <li className="border-t border-gray-100 dark:border-gray-700 mt-1 pt-1">
                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-4 py-2.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 transition rounded-lg font-semibold"
                    >
                      🚪 Cerrar sesión
                    </button>
                  </li>
                )}
              </ul>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
