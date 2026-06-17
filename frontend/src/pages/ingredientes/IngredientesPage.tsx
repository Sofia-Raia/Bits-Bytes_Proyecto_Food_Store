// src/pages/ingredientes/IngredientesPage.tsx
import { useState } from 'react'
import { useIngredientes } from '../../hooks/useIngredientes'
import type { IngredienteSortBy, SortDir } from '../../hooks/useIngredientes'
import { useAuth } from '../../store/authStore'
import type { Ingrediente, IngredienteCreate, IngredienteUpdate } from '../../models/ingrediente'
import Modal from '../../components/ui/Modal'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import IngredienteForm from '../../components/ingredientes/IngredienteForm'
import Pagination from '../../components/ui/Pagination'
import Toast, { useToast } from '../../components/ui/Toast'
import { SkeletonRow } from '../../components/ui/Skeleton'
import { getIngredientesApi } from '../../api/ingredientes'
import { exportToExcel } from '../../utils/exportExcel'

function SortableHeader({ label, field, sortBy, sortDir, onSort, align = 'left' }: {
  label: string; field: IngredienteSortBy; sortBy: IngredienteSortBy; sortDir: SortDir
  onSort: (field: IngredienteSortBy) => void; align?: 'left' | 'center'
}) {
  const active = sortBy === field
  return (
    <th className={`${align === 'center' ? 'text-center' : 'text-left'} px-5 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700 dark:hover:text-gray-200 group`}
      onClick={() => onSort(field)}>
      <span className={`inline-flex items-center gap-1 ${align === 'center' ? 'justify-center' : ''}`}>
        {label}
        <span className={`transition-opacity ${active ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'}`}>
          {active ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
        </span>
      </span>
    </th>
  )
}

export default function IngredientesPage() {
  const { ingredientes, loading, total, page, pageSize, totalPages, setPage, incluirInactivos, toggleInactivos, agregar, editar, desactivar, reactivar, busqueda, setBusqueda, sortBy, sortDir, setSort } = useIngredientes()
  const { user } = useAuth()
  const isAdmin  = user?.roles.includes('ADMIN') ?? false
  const isStock  = user?.roles.includes('STOCK') ?? false
  const puedeGestionarStock = isAdmin || isStock

  const { toasts, addToast, removeToast } = useToast()

  const [modalOpen, setModalOpen]             = useState(false)
  const [editTarget, setEditTarget]           = useState<Ingrediente | null>(null)
  const [deleteTarget, setDeleteTarget]       = useState<Ingrediente | null>(null)
  const [soloAlergenos, setSoloAlergenos]     = useState(false)
  const [exporting, setExporting]             = useState(false)
  const [formDirty, setFormDirty]             = useState(false)
  const [confirmDiscard, setConfirmDiscard]   = useState(false)
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null)
  const [confirmLoading, setConfirmLoading]   = useState(false)

  // ── Modal reponer stock ───────────────────────────────────────────────────
  const [stockTarget, setStockTarget] = useState<Ingrediente | null>(null)
  const [nuevoStock, setNuevoStock]   = useState('')
  const [stockLoading, setStockLoading] = useState(false)

  const filtrados      = ingredientes.filter(i => soloAlergenos ? i.es_alergeno : true)
  const totalAlergenos = ingredientes.filter(i => i.es_alergeno && i.activo).length
  const colCount = isAdmin ? 9 : puedeGestionarStock ? 9 : 8

  const openNew  = () => { setEditTarget(null); setFormDirty(false); setModalOpen(true) }
  const openEdit = (i: Ingrediente) => { setEditTarget(i); setFormDirty(false); setModalOpen(true) }
  const requestClose = () => { if (formDirty) setConfirmDiscard(true); else { setModalOpen(false); setEditTarget(null) } }
  const handleConfirmDiscard = () => { setConfirmDiscard(false); setModalOpen(false); setEditTarget(null); setFormDirty(false) }

  const handleSubmit = async (data: IngredienteCreate | IngredienteUpdate) => {
    try {
      if (editTarget) { await editar(editTarget.id, data); addToast('Ingrediente actualizado', 'success') }
      else { await agregar(data as IngredienteCreate); addToast('Ingrediente creado', 'success') }
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

  const handleReactivar = async (ing: Ingrediente) => {
    setActionLoadingId(ing.id)
    try { await reactivar(ing.id); addToast(`"${ing.nombre}" reactivado`, 'success') }
    catch (err: unknown) { addToast(err instanceof Error ? err.message : 'Error al reactivar', 'error') }
    finally { setActionLoadingId(null) }
  }

  const openStockModal = (ing: Ingrediente) => {
    setStockTarget(ing)
    setNuevoStock(String(ing.stock_cantidad))
  }

  const handleReponerStock = async () => {
    if (!stockTarget) return
    const valor = parseFloat(nuevoStock)
    if (isNaN(valor) || valor < 0) { addToast('El stock debe ser un número ≥ 0', 'error'); return }
    setStockLoading(true)
    try {
      // Usa el contexto editar: actualiza backend (PATCH /ingredientes/{id}) y refresca estado
      await editar(stockTarget.id, { stock_cantidad: valor })
      addToast(`Stock de "${stockTarget.nombre}" actualizado a ${valor.toFixed(3)}`, 'success')
      setStockTarget(null)
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : 'Error al actualizar stock', 'error')
    } finally {
      setStockLoading(false)
    }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const res = await getIngredientesApi(1, 9999, incluirInactivos, busqueda || undefined)
      const rows = res.items.map(i => ({ 'Código': i.codigo, 'Nombre': i.nombre, 'Descripción': i.descripcion ?? '', 'Costo': i.costo, 'Unidad': i.unidad_medida, 'Stock': i.stock_cantidad, 'Alérgeno': i.es_alergeno ? 'Sí' : 'No', 'Estado': i.activo ? 'Activo' : 'Inactivo' }))
      exportToExcel(rows, `ingredientes_${new Date().toISOString().slice(0, 10)}`, 'Ingredientes')
      addToast(`${rows.length} ingredientes exportados`, 'success')
    } catch { addToast('Error al exportar', 'error') }
    finally { setExporting(false) }
  }

  const handleSort = (field: IngredienteSortBy) => {
    if (sortBy === field) setSort(field, sortDir === 'asc' ? 'desc' : 'asc')
    else setSort(field, 'asc')
  }

  const UNIDAD_LABEL: Record<string, string> = { KG: 'kg', L: 'L', UNIDADES: 'u' }

  return (
    <div className="max-w-6xl mx-auto px-1 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">🧂 Ingredientes</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {total} registrado{total !== 1 ? 's' : ''}
            {totalAlergenos > 0 && <span className="ml-2 text-amber-600 dark:text-amber-400 font-medium">· {totalAlergenos} alérgeno{totalAlergenos !== 1 ? 's' : ''}</span>}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExport} disabled={exporting || total === 0}
            className="inline-flex items-center gap-2 bg-emerald-50 dark:bg-emerald-900/30 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 font-semibold px-4 py-2.5 rounded-xl transition border border-emerald-200 dark:border-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed">
            {exporting ? '⏳ Exportando...' : '📥 Excel'}
          </button>
          {puedeGestionarStock && (
            <button onClick={openNew} className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2.5 rounded-xl transition">
              <span className="text-lg">+</span> Nuevo ingrediente
            </button>
          )}
        </div>
      </div>

      {/* Filtros */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5 flex-wrap">
        <input type="text" placeholder="Buscar por código, nombre o descripción..." value={busqueda} onChange={e => setBusqueda(e.target.value)}
          className="flex-1 sm:max-w-sm border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400 text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 placeholder-gray-400 dark:placeholder-gray-500" />
        <label className="flex items-center gap-2 cursor-pointer select-none bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-xl px-4 py-2.5 hover:bg-amber-100 dark:hover:bg-amber-900/30 transition">
          <input type="checkbox" checked={soloAlergenos} onChange={e => setSoloAlergenos(e.target.checked)} className="w-4 h-4 accent-amber-500" />
          <span className="text-sm font-medium text-amber-700 dark:text-amber-400">⚠️ Solo alérgenos</span>
        </label>
        {isAdmin && (
          <label className="flex items-center gap-2 cursor-pointer select-none bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl px-4 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-600 transition">
            <input type="checkbox" checked={incluirInactivos} onChange={toggleInactivos} className="w-4 h-4 accent-gray-500" />
            <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Mostrar inactivos</span>
          </label>
        )}
      </div>

      {(loading || total > 0) && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-100 dark:border-gray-700">
                  <SortableHeader label="Código"   field="codigo"      sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
                  <SortableHeader label="Nombre"   field="nombre"      sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
                  <th className="text-left px-5 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">Descripción</th>
                  <SortableHeader label="Costo"    field="nombre"      sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="center" />
                  <th className="text-center px-5 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Unidad</th>
                  <th className="text-center px-5 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Stock</th>
                  <SortableHeader label="Alérgeno" field="es_alergeno" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} align="center" />
                  <th className="text-center px-5 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Estado</th>
                  {puedeGestionarStock && <th className="text-center px-5 py-3.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Acciones</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
                {loading && Array.from({ length: pageSize }).map((_, i) => <SkeletonRow key={i} cols={colCount} />)}
                {!loading && filtrados.map(ing => (
                  <tr key={ing.id} className={`transition ${!ing.activo ? 'opacity-50 bg-gray-50 dark:bg-gray-700/30' : 'hover:bg-gray-50 dark:hover:bg-gray-700/40'}`}>
                    <td className="px-5 py-4">
                      <span className="font-mono text-xs bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 px-2 py-1 rounded-lg font-semibold">{ing.codigo}</span>
                    </td>
                    <td className="px-5 py-4"><span className="font-medium text-gray-800 dark:text-gray-200">{ing.nombre}</span></td>
                    <td className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400 hidden md:table-cell max-w-xs truncate">
                      {ing.descripcion ?? <span className="italic text-gray-300 dark:text-gray-600">Sin descripción</span>}
                    </td>
                    <td className="px-5 py-4 text-center">
                      <span className="font-medium text-gray-800 dark:text-gray-200">${ing.costo.toFixed(2)}</span>
                      <span className="text-xs text-gray-400 dark:text-gray-500 ml-1">/{ing.unidad_medida.toLowerCase()}</span>
                    </td>
                    <td className="px-5 py-4 text-center">
                      <span className="inline-flex text-xs font-semibold px-2.5 py-1 rounded-full bg-indigo-50 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300">{ing.unidad_medida}</span>
                    </td>
                    <td className="px-5 py-4 text-center">
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${ing.stock_cantidad > 0 ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300' : 'bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300'}`}>
                        {ing.stock_cantidad.toFixed(3)} {UNIDAD_LABEL[ing.unidad_medida] ?? ing.unidad_medida.toLowerCase()}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-center">
                      {ing.es_alergeno
                        ? <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300">⚠️ Sí</span>
                        : <span className="inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">No</span>
                      }
                    </td>
                    <td className="px-5 py-4 text-center">
                      {ing.activo
                        ? <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300">Activo</span>
                        : <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300">Inactivo</span>
                      }
                    </td>
                    {puedeGestionarStock && (
                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {ing.activo ? (
                            <>
                              <button onClick={() => openStockModal(ing)} disabled={actionLoadingId === ing.id}
                                className="text-xs font-medium text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 px-2.5 py-1.5 rounded-lg transition disabled:opacity-40" title="Reponer stock">
                                📦 Stock
                              </button>
                              <button onClick={() => openEdit(ing)} disabled={actionLoadingId === ing.id}
                                className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 px-3 py-1.5 rounded-lg transition disabled:opacity-40">Editar</button>
                              {isAdmin && (
                                <button onClick={() => setDeleteTarget(ing)} disabled={actionLoadingId === ing.id}
                                  className="text-xs font-medium text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 px-3 py-1.5 rounded-lg transition disabled:opacity-40">Desactivar</button>
                              )}
                            </>
                          ) : (
                            isAdmin && (
                              <button onClick={() => handleReactivar(ing)} disabled={actionLoadingId === ing.id}
                                className="text-xs font-medium text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/30 px-3 py-1.5 rounded-lg transition disabled:opacity-40 min-w-[72px]">
                                {actionLoadingId === ing.id ? <span className="flex items-center gap-1 justify-center"><svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" /></svg></span> : 'Reactivar'}
                              </button>
                            )
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!loading && filtrados.length === 0 && soloAlergenos && (
            <div className="text-center py-10 text-gray-400 dark:text-gray-500"><p>Sin alérgenos en esta página</p></div>
          )}
          <div className="px-5 pb-4">
            <Pagination page={page} totalPages={totalPages} total={total} pageSize={pageSize} onPage={setPage} loading={loading} />
          </div>
        </div>
      )}

      {!loading && total === 0 && (
        <div className="text-center py-16 text-gray-400 dark:text-gray-500">
          <p className="text-5xl mb-3">🧂</p>
          <p className="font-medium text-lg">No hay ingredientes registrados</p>
          {puedeGestionarStock && <button onClick={openNew} className="mt-3 text-blue-500 underline text-sm">Crear el primero</button>}
        </div>
      )}

      {/* Modal crear/editar ingrediente */}
      <Modal open={modalOpen} title={editTarget ? `Editar: ${editTarget.nombre}` : 'Nuevo ingrediente'} onClose={requestClose} size="sm">
        <IngredienteForm initial={editTarget} onSubmit={handleSubmit} onCancel={requestClose} onDirtyChange={setFormDirty} />
      </Modal>

      {/* Modal reponer stock */}
      <Modal open={!!stockTarget} title={`📦 Reponer stock — ${stockTarget?.nombre ?? ''}`} onClose={() => !stockLoading && setStockTarget(null)} size="sm">
        <div className="flex flex-col gap-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Stock actual: <span className="font-semibold text-gray-800 dark:text-gray-200">{stockTarget?.stock_cantidad.toFixed(3)} {stockTarget?.unidad_medida.toLowerCase()}</span>
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">Nuevo stock</label>
            <input type="number" value={nuevoStock} onChange={e => setNuevoStock(e.target.value)} min="0" step="0.001" placeholder="0.000"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400 text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700" />
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Este valor reemplaza el stock actual (no suma).</p>
          </div>
          <div className="flex gap-3 justify-end">
            <button type="button" onClick={() => setStockTarget(null)} disabled={stockLoading}
              className="px-4 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-xl transition disabled:opacity-50">Cancelar</button>
            <button type="button" onClick={handleReponerStock} disabled={stockLoading}
              className="px-4 py-2.5 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl transition disabled:opacity-50">
              {stockLoading ? 'Guardando...' : 'Guardar stock'}
            </button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog open={confirmDiscard} title="¿Descartar cambios?" message="Tenés cambios sin guardar. Si cerrás ahora, se van a perder." confirmLabel="Descartar" danger onConfirm={handleConfirmDiscard} onCancel={() => setConfirmDiscard(false)} />
      <ConfirmDialog open={!!deleteTarget} title="Desactivar ingrediente" message={`¿Desactivás "${deleteTarget?.nombre}"? Quedará visible como inactivo y podrás reactivarlo en cualquier momento.`} confirmLabel="Sí, desactivar" danger loading={confirmLoading} onConfirm={handleDesactivar} onCancel={() => !confirmLoading && setDeleteTarget(null)} />
      <Toast toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
