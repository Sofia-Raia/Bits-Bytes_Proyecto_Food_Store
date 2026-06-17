// src/components/productos/AplicarMargenForm.tsx
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getProductosApi } from '../../api/productos'
import { useCategorias } from '../../hooks/useCategorias'
import type { Producto } from '../../models/producto'

export interface MargenFormValues { modo: 'PRODUCTOS' | 'CATEGORIA'; productoIdsSeleccionados: number[]; categoriaId: number | null; margen: number }
interface Props { onPreview: (values: MargenFormValues) => void; loading: boolean }

export default function AplicarMargenForm({ onPreview, loading }: Props) {
  const { data: prodData } = useQuery({
    queryKey: ['productos', 'margen-todos'],
    queryFn: () => getProductosApi(1, 1000, false),
  })
  const productos: Producto[] = prodData?.items ?? []
  const { categorias } = useCategorias()
  const [modo, setModo]                   = useState<'PRODUCTOS' | 'CATEGORIA'>('PRODUCTOS')
  const [busqueda, setBusqueda]           = useState('')
  const [seleccionados, setSeleccionados] = useState<Set<number>>(new Set())
  const [categoriaId, setCategoriaId]     = useState<number | null>(null)
  const [margen, setMargen]               = useState(50)

  const manufacturados: Producto[] = useMemo(() => productos.filter(p => p.tipo === 'MANUFACTURADO' && p.activo), [productos])
  const filtrados = useMemo(() => {
    if (!busqueda.trim()) return manufacturados
    const q = busqueda.toLowerCase()
    return manufacturados.filter(p => p.nombre.toLowerCase().includes(q) || p.codigo.toLowerCase().includes(q))
  }, [manufacturados, busqueda])

  const toggleProducto = (id: number) => { setSeleccionados(prev => { const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next }) }
  const toggleTodos = () => { if (seleccionados.size === filtrados.length) setSeleccionados(new Set()); else setSeleccionados(new Set(filtrados.map(p => p.id))) }
  const handlePreview = () => { onPreview({ modo, productoIdsSeleccionados: modo === 'PRODUCTOS' ? [...seleccionados] : [], categoriaId: modo === 'CATEGORIA' ? categoriaId : null, margen }) }
  const puedeCalcular = margen > 0 && (modo === 'CATEGORIA' ? categoriaId !== null : seleccionados.size > 0)

  const inputCls = "w-full border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500"

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Aplicar a:</p>
        <div className="flex gap-2">
          {(['PRODUCTOS', 'CATEGORIA'] as const).map(m => (
            <button key={m} type="button" onClick={() => setModo(m)}
              className={`flex-1 px-4 py-2.5 rounded-xl text-sm font-medium border-2 transition ${
                modo === m ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-500'
              }`}>
              {m === 'PRODUCTOS' ? '🍽️ Productos individuales' : '📂 Categoría'}
            </button>
          ))}
        </div>
      </div>

      {modo === 'PRODUCTOS' && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-200">Productos MANUFACTURADOS <span className="ml-1.5 text-xs text-gray-400 dark:text-gray-500">({seleccionados.size} seleccionados)</span></p>
            {filtrados.length > 0 && <button type="button" onClick={toggleTodos} className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 font-medium">{seleccionados.size === filtrados.length ? 'Deseleccionar todos' : 'Seleccionar todos'}</button>}
          </div>
          <input type="text" value={busqueda} onChange={e => setBusqueda(e.target.value)} placeholder="Buscar productos..." className={`${inputCls} mb-3`} />
          {manufacturados.length === 0
            ? <p className="text-sm text-gray-400 dark:text-gray-500 italic text-center py-6">No hay productos MANUFACTURADOS activos.</p>
            : (
              <div className="border border-gray-200 dark:border-gray-600 rounded-xl max-h-64 overflow-y-auto divide-y divide-gray-50 dark:divide-gray-700">
                {filtrados.map(p => (
                  <label key={p.id} className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-700/40 cursor-pointer">
                    <input type="checkbox" checked={seleccionados.has(p.id)} onChange={() => toggleProducto(p.id)} className="w-4 h-4 accent-blue-600 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{p.nombre}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500">{p.codigo} · Costo: ${p.precio_costo.toFixed(2)}</p>
                    </div>
                    <span className="text-sm font-semibold text-gray-600 dark:text-gray-300 shrink-0">${p.precio_base.toFixed(2)}</span>
                  </label>
                ))}
                {filtrados.length === 0 && <p className="text-sm text-gray-400 dark:text-gray-500 italic text-center py-6">Sin resultados.</p>}
              </div>
            )}
        </div>
      )}

      {modo === 'CATEGORIA' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">Categoría</label>
          <select value={categoriaId ?? ''} onChange={e => setCategoriaId(e.target.value ? Number(e.target.value) : null)}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200">
            <option value="">Seleccioná una categoría...</option>
            {categorias.filter(c => c.activo).map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </select>
          {categoriaId && <p className="text-xs text-blue-600 dark:text-blue-400 mt-1.5">ℹ️ Incluye todos los productos de esta categoría y sus subcategorías (recursivamente).</p>}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">Margen (%)</label>
        <div className="flex items-center gap-2">
          <input type="number" min={0} max={999} step={0.5} value={margen} onChange={e => setMargen(Number(e.target.value))}
            className="w-32 border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200" />
          <span className="text-sm text-gray-500 dark:text-gray-400">— precio nuevo = costo × (1 + margen/100)</span>
        </div>
      </div>

      <button type="button" onClick={handlePreview} disabled={!puedeCalcular || loading}
        className="w-full py-2.5 bg-orange-500 hover:bg-orange-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl text-sm font-semibold text-white transition">
        {loading ? 'Calculando...' : '🔍 Calcular preview'}
      </button>
    </div>
  )
}
