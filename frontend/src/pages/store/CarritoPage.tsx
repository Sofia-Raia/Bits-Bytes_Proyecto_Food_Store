// src/pages/store/CarritoPage.tsx
import { Link, useNavigate } from 'react-router-dom'
import { useCarrito } from '../../store/carritoStore'
import { useAuth } from '../../store/authStore'

function formatPrecio(n: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)
}

export default function CarritoPage() {
  const { items, totalPrecio, quitarItem, cambiarCantidad, vaciarCarrito } = useCarrito()
  const { user } = useAuth()
  const navigate = useNavigate()

  const handleFinalizar = () => {
    if (!user) {
      navigate('/login', { state: { from: '/store/checkout' } })
    } else {
      navigate('/store/checkout')
    }
  }

  if (items.length === 0) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-20 text-center">
        <p className="text-6xl mb-4">🛒</p>
        <h2 className="text-2xl font-bold text-gray-700 dark:text-gray-200 mb-2">Tu carrito está vacío</h2>
        <p className="text-gray-500 dark:text-gray-400 mb-6">Explorá nuestra tienda y agregá productos.</p>
        <Link
          to="/store"
          className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-xl transition"
        >
          🛍️ Ir a la tienda
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">🛒 Carrito de compras</h1>
        <button
          onClick={vaciarCarrito}
          className="text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 hover:underline font-medium transition"
        >
          🗑 Vaciar carrito
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden mb-6">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-100 dark:border-gray-700">
            <tr>
              <th className="text-left px-5 py-3.5 font-semibold text-gray-600 dark:text-gray-300">Producto</th>
              <th className="text-center px-4 py-3.5 font-semibold text-gray-600 dark:text-gray-300 w-28">Cantidad</th>
              <th className="text-right px-4 py-3.5 font-semibold text-gray-600 dark:text-gray-300 w-32">Precio unit.</th>
              <th className="text-right px-4 py-3.5 font-semibold text-gray-600 dark:text-gray-300 w-32">Subtotal</th>
              <th className="px-4 py-3.5 w-12" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
            {items.map(item => (
              <tr key={item.producto_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition">
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center overflow-hidden shrink-0">
                      {item.imagen_url ? (
                        <img src={item.imagen_url} alt={item.nombre} className="w-full h-full object-cover" />
                      ) : (
                        <span className="text-2xl">🍽️</span>
                      )}
                    </div>
                    <span className="font-medium text-gray-800 dark:text-gray-100">{item.nombre}</span>
                  </div>
                </td>
                <td className="px-4 py-4 text-center">
                  <input
                    type="number"
                    min={1}
                    value={item.cantidad}
                    onChange={e => cambiarCantidad(item.producto_id, Number(e.target.value))}
                    className="w-16 text-center border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1 text-sm
                      bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100
                      focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                </td>
                <td className="px-4 py-4 text-right text-gray-700 dark:text-gray-300">
                  {formatPrecio(item.precio_base)}
                </td>
                <td className="px-4 py-4 text-right font-semibold text-gray-800 dark:text-gray-100">
                  {formatPrecio(item.precio_base * item.cantidad)}
                </td>
                <td className="px-4 py-4 text-center">
                  <button
                    onClick={() => quitarItem(item.producto_id)}
                    aria-label="Quitar"
                    className="text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 transition text-lg leading-none"
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Total y acciones */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <Link to="/store" className="text-sm text-blue-600 dark:text-blue-400 hover:underline">
          ← Seguir comprando
        </Link>

        <div className="flex flex-col items-end gap-3">
          <div className="text-xl font-bold text-gray-800 dark:text-gray-100">
            Total: <span className="text-blue-700 dark:text-blue-400">{formatPrecio(totalPrecio)}</span>
          </div>
          <button
            onClick={handleFinalizar}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-8 py-3 rounded-xl transition text-sm"
          >
            Finalizar pedido →
          </button>
        </div>
      </div>
    </div>
  )
}
