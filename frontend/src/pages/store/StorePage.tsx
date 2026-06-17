// src/pages/store/StorePage.tsx
import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getProductosApi } from '../../api/productos'
import { getCategoriasApi } from '../../api/categorias'
import type { Producto } from '../../models/producto'
import Pagination from '../../components/ui/Pagination'
import Toast, { useToast } from '../../components/ui/Toast'
import { useCarrito } from '../../store/carritoStore'
import { qk } from '../../queries/keys'

const PAGE_SIZE = 12

function formatPrecio(n: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)
}

function ProductCard({ producto, onAgregar }: { producto: Producto; onAgregar: () => void }) {
  const sinStock = producto.stock_cantidad === 0
  const categoriaPrincipal = producto.categorias.find(c => c.es_principal)
  const imagenUrl = producto.imagenes_url?.[0]

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 flex flex-col overflow-hidden hover:shadow-md transition">
      {/* Imagen */}
      <div className="h-44 bg-gray-100 dark:bg-gray-700 flex items-center justify-center overflow-hidden">
        {imagenUrl ? (
          <img
            src={imagenUrl}
            alt={producto.nombre}
            className="w-full h-full object-cover"
            onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
          />
        ) : (
          <span className="text-5xl">🍽️</span>
        )}
      </div>

      <div className="p-4 flex flex-col gap-2 flex-1">
        {/* Categoría */}
        {categoriaPrincipal && (
          <span className="text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded-full w-fit">
            {categoriaPrincipal.nombre}
          </span>
        )}

        <h3 className="font-bold text-gray-800 dark:text-gray-100 leading-tight">{producto.nombre}</h3>

        {producto.descripcion && (
          <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">{producto.descripcion}</p>
        )}

        <div className="flex items-center justify-between mt-auto pt-2 gap-2">
          <span className="font-bold text-blue-700 dark:text-blue-400 text-lg">{formatPrecio(producto.precio_base)}</span>
          {sinStock && (
            <span className="text-xs font-semibold bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 px-2 py-0.5 rounded-full">
              Sin stock
            </span>
          )}
        </div>

        <button
          disabled={sinStock}
          onClick={onAgregar}
          className="w-full mt-1 py-2 px-4 rounded-xl text-sm font-semibold transition
            bg-blue-600 hover:bg-blue-700 text-white
            disabled:bg-gray-200 dark:disabled:bg-gray-700
            disabled:text-gray-400 dark:disabled:text-gray-500
            disabled:cursor-not-allowed"
        >
          {sinStock ? 'Sin stock' : '🛒 Agregar al carrito'}
        </button>
      </div>
    </div>
  )
}

export default function StorePage() {
  const { agregarItem } = useCarrito()
  const { toasts, addToast, removeToast } = useToast()

  const [busqueda,   setBusqueda]   = useState('')
  const [page,       setPage]       = useState(1)
  const [categoriaId, setCategoriaId] = useState<number | null>(null)

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [busquedaActiva, setBusquedaActiva] = useState('')

  // Catálogo de categorías para el filtro (solo activas).
  const categoriasQuery = useQuery({
    queryKey: qk.categorias.list(false),
    queryFn: () => getCategoriasApi(1, 100, false),
  })
  const categorias = categoriasQuery.data?.items ?? []

  // Catálogo público: no requiere sesión, así que la query siempre está activa.
  const productosQuery = useQuery({
    queryKey: qk.productos.publico(page, busquedaActiva, categoriaId),
    queryFn: () => getProductosApi(
      page, PAGE_SIZE, false, busquedaActiva || undefined,
      'nombre', 'asc', categoriaId ?? undefined,
    ),
  })

  const productos: Producto[] = productosQuery.data?.items ?? []
  const total = productosQuery.data?.total ?? 0
  const loading = productosQuery.isLoading
  const error = productosQuery.error ? 'Error al cargar el catálogo. Intentá de nuevo.' : ''
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // Debounce de búsqueda
  const handleBusqueda = (value: string) => {
    setBusqueda(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setBusquedaActiva(value)
      setPage(1)
    }, 400)
  }

  const handleCategoria = (value: string) => {
    setCategoriaId(value ? Number(value) : null)
    setPage(1)
  }

  const handleAgregar = (producto: Producto) => {
    agregarItem(producto)
    addToast(`${producto.nombre} agregado al carrito ✓`, 'success')
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">🛍️ Tienda</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Explorá nuestro catálogo de productos</p>
        </div>
        <Link
          to="/store/carrito"
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2.5 rounded-xl transition text-sm"
        >
          🛒 Ver carrito
        </Link>
      </div>

      {/* Búsqueda + filtro por categoría */}
      <div className="mb-6 flex flex-col sm:flex-row gap-3">
        <input
          type="text"
          placeholder="Buscar productos..."
          value={busqueda}
          onChange={e => handleBusqueda(e.target.value)}
          className="w-full max-w-md border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-2.5
            bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100
            placeholder-gray-400 dark:placeholder-gray-500
            focus:outline-none focus:ring-2 focus:ring-blue-400 text-sm"
        />
        <select
          value={categoriaId ?? ''}
          onChange={e => handleCategoria(e.target.value)}
          className="w-full sm:w-56 border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-2.5
            bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100
            focus:outline-none focus:ring-2 focus:ring-blue-400 text-sm"
        >
          <option value="">Todas las categorías</option>
          {categorias.map(c => (
            <option key={c.id} value={c.id}>{c.nombre}</option>
          ))}
        </select>
      </div>

      {/* Estado de error */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-xl p-4 text-red-700 dark:text-red-300 text-sm mb-6">
          {error}
        </div>
      )}

      {/* Grid de productos */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
          {Array.from({ length: PAGE_SIZE }).map((_, i) => (
            <div key={i} className="bg-white dark:bg-gray-800 rounded-2xl h-72 animate-pulse border border-gray-100 dark:border-gray-700">
              <div className="h-44 bg-gray-200 dark:bg-gray-700 rounded-t-2xl" />
              <div className="p-4 space-y-2">
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded w-full" />
              </div>
            </div>
          ))}
        </div>
      ) : productos.length === 0 ? (
        <div className="text-center py-20 text-gray-400 dark:text-gray-500">
          <p className="text-5xl mb-4">🔍</p>
          <p className="font-semibold">No se encontraron productos</p>
          {(busquedaActiva || categoriaId) && (
            <button
              onClick={() => { setBusqueda(''); setBusquedaActiva(''); setCategoriaId(null); setPage(1) }}
              className="mt-3 text-sm text-blue-600 dark:text-blue-400 hover:underline"
            >
              Limpiar filtros
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
            {productos.map(p => (
              <ProductCard key={p.id} producto={p} onAgregar={() => handleAgregar(p)} />
            ))}
          </div>

          <div className="mt-6">
            <Pagination
              page={page}
              totalPages={totalPages}
              total={total}
              pageSize={PAGE_SIZE}
              onPage={setPage}
              loading={loading}
            />
          </div>
        </>
      )}

      <Toast toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
