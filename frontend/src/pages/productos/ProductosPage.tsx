// src/pages/productos/ProductosPage.tsx
import { useState } from 'react'
import { useProductos } from '../../hooks/useProductos'
import type { ProductoSortBy, SortDir } from '../../hooks/useProductos'
import { useCategorias } from '../../hooks/useCategorias'
import { useAuth } from '../../store/authStore'
import type { Producto, ProductoCreate, ProductoUpdate } from '../../models/producto'
import Modal from '../../components/ui/Modal'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import ProductoForm from '../../components/productos/ProductoForm'
import Pagination from '../../components/ui/Pagination'
import Toast, { useToast } from '../../components/ui/Toast'
import { SkeletonRow } from '../../components/ui/Skeleton'
import { getProductosApi } from '../../api/productos'
import { exportToExcel } from '../../utils/exportExcel'
import { useQuery } from '@tanstack/react-query'
import { getIngredientesApi } from '../../api/ingredientes'

function SortableHeader({ label, field, sortBy, sortDir, onSort }: {
  label: string; field: ProductoSortBy; sortBy: ProductoSortBy; sortDir: SortDir; onSort: (f: ProductoSortBy) => void
}) {
  const active = sortBy === field
  return (
    <th className="text-center px-4 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700 dark:hover:text-gray-200 group"
      onClick={() => onSort(field)}>
      <span className="inline-flex items-center gap-1">
        {label}
        <span className={`transition-opacity ${active ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'}`}>
          {active ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
        </span>
      </span>
    </th>
  )
}

function TipoBadge({ tipo }: { tipo: Producto['tipo'] }) {
  if (tipo === 'MANUFACTURADO')
    return <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300">MANUFACT.</span>
  return <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">TERMINADO</span>
}

function StockBadge({ stock, disponible, activo, tipo }: { stock: number; disponible: boolean; activo: boolean; tipo: Producto['tipo'] }) {
  if (!activo)                     return <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300">Inactivo</span>
  if (!disponible)                 return <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">No disp.</span>
  if (tipo === 'MANUFACTURADO')    return <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500" title="Stock gestionado por ingredientes">—</span>
  if (stock === 0)                 return <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300">Sin stock</span>
  return <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300">{stock}</span>
}

export default function ProductosPage() {
  const { productos, loading, total, page, pageSize, totalPages, setPage, incluirInactivos, toggleInactivos, agregar, editar, desactivar, reactivar, busqueda, setBusqueda, sortBy, sortDir, setSort, categoriaId, setCategoria } = useProductos()
  const { data: ingData } = useQuery({
  queryKey: ['ingredientes', 'todos'],
  queryFn: () => getIngredientesApi(1, 1000),
})
const ingredientes = ingData?.items ?? []
  const { categorias }   = useCategorias()
  const { user }         = useAuth()
  const isAdmin          = user?.roles.includes('ADMIN') ?? false
  const isStock          = user?.roles.includes('STOCK') ?? false
  const isClient         = user?.roles.includes('CLIENT') ?? false
  const puedeGestionar   = isAdmin || isStock

  const { toasts, addToast, removeToast } = useToast()
  const [modalOpen, setModalOpen]             = useState(false)
  const [editTarget, setEditTarget]           = useState<Producto | null>(null)
  const [deleteTarget, setDeleteTarget]       = useState<Producto | null>(null)
  const [exporting, setExporting]             = useState(false)
  const [formDirty, setFormDirty]             = useState(false)
  const [confirmDiscard, setConfirmDiscard]   = useState(false)
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null)
  const [confirmLoading, setConfirmLoading]   = useState(false)

  const colCount = puedeGestionar ? 9 : isClient ? 3 : 8

  const openNew  = () => { setEditTarget(null); setFormDirty(false); setModalOpen(true) }
  const openEdit = (p: Producto) => { setEditTarget(p); setFormDirty(false); setModalOpen(true) }
  const requestClose = () => { if (formDirty) setConfirmDiscard(true); else { setModalOpen(false); setEditTarget(null) } }
  const handleConfirmDiscard = () => { setConfirmDiscard(false); setModalOpen(false); setEditTarget(null); setFormDirty(false) }

  const handleSubmit = async (data: ProductoCreate | ProductoUpdate) => {
    try {
      if (editTarget) { await editar(editTarget.id, data); addToast('Producto actualizado', 'success') }
      else { await agregar(data as ProductoCreate); addToast('Producto creado', 'success') }
      setModalOpen(false); setEditTarget(null); setFormDirty(false)
    } catch (err: unknown) { throw err }
  }

  const handleDesactivar = async () => {
    if (!deleteTarget) return
    setConfirmLoading(true)
    try { await desactivar(deleteTarget.id); addToast(`"${deleteTarget.nombre}" desactivado`, 'success') }
    catch (err: unknown) { addToast(err instanceof Error ? err.message : 'Error al desactivar', 'error') }
    finally { setConfirmLoading(false); setDeleteTarget(null) }
  }

  const handleReactivar = async (p: Producto) => {
    setActionLoadingId(p.id)
    try { await reactivar(p.id); addToast(`"${p.nombre}" reactivado`, 'success') }
    catch (err: unknown) { addToast(err instanceof Error ? err.message : 'Error al reactivar', 'error') }
    finally { setActionLoadingId(null) }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const res = await getProductosApi(1, 9999, incluirInactivos, busqueda || undefined, sortBy, sortDir, categoriaId ?? undefined)
      const rows = res.items.map(p => ({ 'Código': p.codigo, 'Nombre': p.nombre, 'Descripción': p.descripcion ?? '', 'Tipo': p.tipo, 'Precio Base': p.precio_base, 'Precio Costo': p.precio_costo, 'Stock': p.stock_cantidad, 'Disponible': p.disponible ? 'Sí' : 'No', 'Cat. Principal': p.categorias.find(c => c.es_principal)?.nombre ?? '', 'Categorías': p.categorias.map(c => c.nombre).join(', '), 'Ingredientes': p.ingredientes.map(i => i.nombre).join(', '), 'Estado': p.activo ? 'Activo' : 'Inactivo' }))
      exportToExcel(rows, `productos_${new Date().toISOString().slice(0, 10)}`, 'Productos')
      addToast(`${rows.length} productos exportados`, 'success')
    } catch { addToast('Error al exportar', 'error') }
    finally { setExporting(false) }
  }

  const handleSort = (field: ProductoSortBy) => {
    if (sortBy === field) setSort(field, sortDir === 'asc' ? 'desc' : 'asc')
    else setSort(field, 'asc')
  }

  return (
    <div className="max-w-none px-6 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">🍽️ Productos</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{total} producto{total !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExport} disabled={exporting || total === 0}
            className="inline-flex items-center gap-2 bg-emerald-50 dark:bg-emerald-900/30 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 font-semibold px-4 py-2.5 rounded-xl transition border border-emerald-200 dark:border-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed">
            {exporting ? '⏳ Exportando...' : '📥 Excel'}
          </button>
          {puedeGestionar && (
            <button onClick={openNew} className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2.5 rounded-xl transition">
              <span className="text-lg">+</span> Nuevo producto
            </button>
          )}
        </div>
      </div>

      {/* Filtros */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5 flex-wrap">
        <input type="text" placeholder="Buscar por código o nombre..." value={busqueda} onChange={e => setBusqueda(e.target.value)}
          className="flex-1 sm:max-w-xs border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400 text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 placeholder-gray-400 dark:placeholder-gray-500" />
        <select value={categoriaId ?? ''} onChange={e => setCategoria(e.target.value ? Number(e.target.value) : null)}
          className="border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400 text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700">
          <option value="">Todas las categorías</option>
          {categorias.filter(c => c.activo).map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
        </select>
        {isAdmin && (
          <label className="flex items-center gap-2 cursor-pointer select-none bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl px-4 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-600 transition">
            <input type="checkbox" checked={incluirInactivos} onChange={toggleInactivos} className="w-4 h-4 accent-gray-500" />
            <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Mostrar inactivos</span>
          </label>
        )}
      </div>

      {/* Tabla */}
      {(loading || total > 0) && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-100 dark:border-gray-700">
                  {!isClient && <SortableHeader label="Código" field="codigo" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />}
                  <SortableHeader label="Nombre" field="nombre" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
                  <th className="text-left px-4 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden lg:table-cell">Descripción</th>
                  {!isClient && <th className="text-center px-4 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Tipo</th>}
                  {!isClient && <SortableHeader label="Stock" field="stock_cantidad" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />}
                  {!isClient && <th className="text-left px-4 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">Cat. Principal</th>}
                  <SortableHeader label="Precio" field="precio_base" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
                  {!isClient && <th className="text-center px-4 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Estado</th>}
                  {puedeGestionar && <th className="text-center px-4 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Acciones</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
                {loading && Array.from({ length: pageSize }).map((_, i) => <SkeletonRow key={i} cols={colCount} />)}
                {!loading && productos.map(p => {
                  const catPrincipal = p.categorias.find(c => c.es_principal)?.nombre ?? '—'
                  return (
                    <tr key={p.id} className={`transition ${!p.activo ? 'opacity-50 bg-gray-50 dark:bg-gray-700/30' : 'hover:bg-gray-50 dark:hover:bg-gray-700/40'}`}>
                      {!isClient && (
                        <td className="px-4 py-3.5">
                          <span className="font-mono text-xs bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 px-2 py-1 rounded-lg font-semibold whitespace-nowrap">{p.codigo}</span>
                        </td>
                      )}
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2">
                          {(p.imagenes_url?.[0])
                            ? <img src={p.imagenes_url[0]} alt={p.nombre} className="w-8 h-8 rounded-lg object-cover flex-shrink-0 bg-gray-100 dark:bg-gray-700" onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
                            : <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-900/30 dark:to-indigo-900/30 flex items-center justify-center flex-shrink-0 text-sm">🍽️</div>
                          }
                          <span className="font-medium text-gray-800 dark:text-gray-200 text-sm">{p.nombre}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-sm text-gray-500 dark:text-gray-400 hidden lg:table-cell max-w-xs">
                        <p className="truncate">{p.descripcion ?? <span className="italic text-gray-300 dark:text-gray-600">—</span>}</p>
                      </td>
                      {!isClient && <td className="px-4 py-3.5 text-center"><TipoBadge tipo={p.tipo} /></td>}
                      {!isClient && <td className="px-4 py-3.5 text-center"><StockBadge stock={p.stock_cantidad} disponible={p.disponible} activo={p.activo} tipo={p.tipo} /></td>}
                      {!isClient && <td className="px-4 py-3.5 text-sm text-gray-600 dark:text-gray-400 hidden md:table-cell">{catPrincipal}</td>}
                      <td className="px-4 py-3.5 text-center">
                        <span className="font-semibold text-gray-800 dark:text-gray-200 text-sm whitespace-nowrap">${p.precio_base.toFixed(2)}</span>
                        {!isClient && p.tipo === 'MANUFACTURADO' && p.precio_costo > 0 && (
                          <p className="text-xs text-gray-400 dark:text-gray-500">costo: ${p.precio_costo.toFixed(2)}</p>
                        )}
                      </td>
                      {!isClient && (
                        <td className="px-4 py-3.5 text-center">
                          {p.activo
                            ? <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300">Activo</span>
                            : <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300">Inactivo</span>
                          }
                        </td>
                      )}
                      {puedeGestionar && (
                        <td className="px-4 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-1">
                            {p.activo ? (
                              <>
                                <button onClick={() => openEdit(p)} disabled={actionLoadingId === p.id}
                                  className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 px-3 py-1.5 rounded-lg transition disabled:opacity-40">Editar</button>
                                {isAdmin && (
                                  <button onClick={() => setDeleteTarget(p)} disabled={actionLoadingId === p.id}
                                    className="text-xs font-medium text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 px-3 py-1.5 rounded-lg transition disabled:opacity-40">Desactivar</button>
                                )}
                              </>
                            ) : (
                              isAdmin && (
                                <button onClick={() => handleReactivar(p)} disabled={actionLoadingId === p.id}
                                  className="text-xs font-medium text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/30 px-3 py-1.5 rounded-lg transition disabled:opacity-40 min-w-[72px]">
                                  {actionLoadingId === p.id ? <span className="flex items-center gap-1 justify-center"><svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" /></svg></span> : 'Reactivar'}
                                </button>
                              )
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <div className="px-5 pb-4">
            <Pagination page={page} totalPages={totalPages} total={total} pageSize={pageSize} onPage={setPage} loading={loading} />
          </div>
        </div>
      )}

      {!loading && total === 0 && (
        <div className="text-center py-16 text-gray-400 dark:text-gray-500">
          {(categoriaId !== null || busqueda) ? (
            <>
              <p className="text-5xl mb-3">🔍</p>
              <p className="font-medium text-lg">Sin productos para este filtro</p>
              <button onClick={() => { setCategoria(null); setBusqueda('') }} className="mt-3 text-blue-500 underline text-sm">Limpiar filtros</button>
            </>
          ) : (
            <>
              <p className="text-5xl mb-3">🍽️</p>
              <p className="font-medium text-lg">No hay productos registrados</p>
              {puedeGestionar && <button onClick={openNew} className="mt-3 text-blue-500 underline text-sm">Crear el primero</button>}
            </>
          )}
        </div>
      )}

      <Modal open={modalOpen} title={editTarget ? `Editar: ${editTarget.nombre}` : 'Nuevo producto'} onClose={requestClose} size="lg">
        <ProductoForm initial={editTarget} categorias={categorias.filter(c => c.activo)} ingredientes={ingredientes.filter(i => i.activo)} onSubmit={handleSubmit} onCancel={requestClose} onDirtyChange={setFormDirty} />
      </Modal>
      <ConfirmDialog open={confirmDiscard} title="¿Descartar cambios?" message="Tenés cambios sin guardar. Si cerrás ahora, se van a perder." confirmLabel="Descartar" danger onConfirm={handleConfirmDiscard} onCancel={() => setConfirmDiscard(false)} />
      <ConfirmDialog open={!!deleteTarget} title="Desactivar producto" message={`¿Desactivás "${deleteTarget?.nombre}"? Se marcará como no disponible. Podrás reactivarlo en cualquier momento.`} confirmLabel="Sí, desactivar" danger loading={confirmLoading} onConfirm={handleDesactivar} onCancel={() => !confirmLoading && setDeleteTarget(null)} />
      <Toast toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
