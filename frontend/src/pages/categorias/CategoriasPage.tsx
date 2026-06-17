// src/pages/categorias/CategoriasPage.tsx
import { useState } from 'react'
import { useCategorias } from '../../hooks/useCategorias'
import { useAuth } from '../../store/authStore'
import type { CategoriaTree, Categoria, CategoriaCreate, CategoriaUpdate } from '../../models/categoria'
import Modal from '../../components/ui/Modal'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import CategoriaForm from '../../components/categorias/CategoriaForm'
import CategoriaTreeNode from '../../components/categorias/CategoriaTreeNode'
import Toast, { useToast } from '../../components/ui/Toast'

export default function CategoriasPage() {
  const { categorias, tree, loading, total, incluirInactivos, toggleInactivos, agregar, editar, desactivar, reactivar, busqueda, setBusqueda } = useCategorias()
  const { user }  = useAuth()
  const isAdmin   = user?.roles.includes('ADMIN') ?? false
  const { toasts, addToast, removeToast } = useToast()

  const [modalOpen, setModalOpen]       = useState(false)
  const [editTarget, setEditTarget]     = useState<Categoria | null>(null)
  const [parentPreset, setParentPreset] = useState<number | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<CategoriaTree | null>(null)

  const openNew      = () => { setEditTarget(null); setParentPreset(null); setModalOpen(true) }
  const openEdit     = (c: CategoriaTree | Categoria) => { setEditTarget(c as Categoria); setParentPreset(null); setModalOpen(true) }
  const openAddChild = (parent: CategoriaTree) => { setEditTarget(null); setParentPreset(parent.id); setModalOpen(true) }
  const closeModal   = () => { setModalOpen(false); setEditTarget(null); setParentPreset(null) }

  const handleSubmit = async (data: CategoriaCreate | CategoriaUpdate) => {
    try {
      if (editTarget) { await editar(editTarget.id, data); addToast('Categoría actualizada', 'success') }
      else { await agregar((parentPreset ? { ...data, parent_id: parentPreset } : data) as CategoriaCreate); addToast('Categoría creada', 'success') }
      closeModal()
    } catch (err: unknown) { throw err }
  }

  const handleDesactivar = async () => {
    if (!deleteTarget) return
    try { await desactivar(deleteTarget.id); addToast(`"${deleteTarget.nombre}" desactivada`, 'success') }
    catch (err: unknown) { addToast(err instanceof Error ? err.message : 'Error al desactivar', 'error') }
    finally { setDeleteTarget(null) }
  }

  const handleReactivar = async (cat: CategoriaTree) => {
    try { await reactivar(cat.id); addToast(`"${cat.nombre}" reactivada`, 'success') }
    catch (err: unknown) { addToast(err instanceof Error ? err.message : 'Error al reactivar', 'error') }
  }

  const modalTitle = editTarget ? `Editar: ${editTarget.nombre}` : parentPreset ? `Nueva subcategoría en "${categorias.find(c => c.id === parentPreset)?.nombre}"` : 'Nueva categoría'

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">📂 Categorías</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{total} categoría{total !== 1 ? 's' : ''} — vista en árbol</p>
        </div>
        {isAdmin && (
          <button onClick={openNew} className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2.5 rounded-xl transition">
            <span className="text-lg">+</span> Nueva categoría
          </button>
        )}
      </div>

      {isAdmin && (
        <div className="mb-4">
          <label className="inline-flex items-center gap-2 cursor-pointer select-none bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl px-4 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-600 transition">
            <input type="checkbox" checked={incluirInactivos} onChange={toggleInactivos} className="w-4 h-4 accent-gray-500" />
            <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Mostrar categorías inactivas</span>
          </label>
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-blue-600 border-t-transparent" />
        </div>
      )}

      {!loading && tree.length === 0 && (
        <div className="text-center py-16 text-gray-400 dark:text-gray-500">
          <p className="text-5xl mb-3">📂</p>
          <p className="font-medium text-lg">No hay categorías registradas</p>
          {isAdmin && <button onClick={openNew} className="mt-3 text-blue-500 underline text-sm">Crear la primera</button>}
        </div>
      )}

      {!loading && tree.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
          {isAdmin && <p className="text-xs text-gray-400 dark:text-gray-500 mb-3 px-2">Pasá el cursor sobre una categoría para ver las acciones</p>}
          {tree.map(node => (
            <CategoriaTreeNode key={node.id} node={node} isAdmin={isAdmin} onEdit={openEdit} onDesactivar={setDeleteTarget} onReactivar={handleReactivar} onAddChild={openAddChild} />
          ))}
        </div>
      )}

      {!loading && categorias.length > 0 && (
        <details className="mt-4">
          <summary className="text-sm text-gray-400 dark:text-gray-500 cursor-pointer hover:text-gray-600 dark:hover:text-gray-300">
            Ver lista plana ({categorias.length} registros)
          </summary>
          <div className="mt-2 bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {categorias.map(c => (
                <div key={c.id} className={`flex items-center gap-2 text-sm ${!c.activo ? 'opacity-50' : 'text-gray-600 dark:text-gray-300'}`}>
                  <span className="font-mono text-xs bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 px-1.5 py-0.5 rounded">{c.codigo}</span>
                  <span className="font-medium">{c.nombre}</span>
                  {c.parent_id && <span className="text-xs text-gray-400 dark:text-gray-500">↑ {c.parent_id}</span>}
                  {!c.activo && <span className="text-xs text-red-400 dark:text-red-500">(inactivo)</span>}
                </div>
              ))}
            </div>
          </div>
        </details>
      )}

      <Modal open={modalOpen} title={modalTitle} onClose={closeModal} size="sm">
        <CategoriaForm initial={editTarget} categorias={categorias.filter(c => c.activo)} onSubmit={handleSubmit} onCancel={closeModal} />
      </Modal>
      <ConfirmDialog
        open={!!deleteTarget} title="Desactivar categoría"
        message={(deleteTarget?.subcategorias ?? []).filter(s => s.activo).length > 0 ? `"${deleteTarget?.nombre}" tiene subcategorías activas. Desactiválas primero.` : `¿Desactivás "${deleteTarget?.nombre}"? Podrás reactivarla en cualquier momento.`}
        confirmLabel="Sí, desactivar" danger
        onConfirm={(deleteTarget?.subcategorias ?? []).filter(s => s.activo).length > 0 ? () => { addToast('Desactivá las subcategorías primero', 'error'); setDeleteTarget(null) } : handleDesactivar}
        onCancel={() => setDeleteTarget(null)}
      />
      <Toast toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
