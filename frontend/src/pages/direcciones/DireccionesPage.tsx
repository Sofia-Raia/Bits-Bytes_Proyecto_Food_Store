// src/pages/direcciones/DireccionesPage.tsx
import { useState } from 'react'
import { useDirecciones } from '../../hooks/useDirecciones'
import type { Direccion } from '../../models/direccion'
import { formatDireccion } from '../../models/direccion'
import Modal from '../../components/ui/Modal'
import Toast, { useToast } from '../../components/ui/Toast'
import DireccionForm from '../../components/direcciones/DireccionForm'
import { ApiError } from '../../api/client'

function DireccionCard({ direccion, onEditar, onEliminar, onMarcarPrincipal, loadingId }: {
  direccion: Direccion; onEditar: (d: Direccion) => void; onEliminar: (d: Direccion) => void
  onMarcarPrincipal: (d: Direccion) => void; loadingId: number | null
}) {
  const cargando = loadingId === direccion.id
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-2xl border-2 p-5 shadow-sm transition ${
      direccion.es_principal ? 'border-blue-400 dark:border-blue-500' : 'border-gray-100 dark:border-gray-700 hover:border-gray-200 dark:hover:border-gray-600'
    }`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-lg">📍</span>
          {direccion.alias && <span className="font-semibold text-gray-800 dark:text-gray-100">{direccion.alias}</span>}
          {direccion.es_principal && (
            <span className="inline-flex items-center gap-1 text-xs font-semibold bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700 px-2 py-0.5 rounded-full">⭐ Principal</span>
          )}
        </div>
      </div>
      <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{formatDireccion(direccion)}</p>
      <div className="flex gap-2 mt-4 flex-wrap">
        <button onClick={() => onEditar(direccion)} disabled={cargando}
          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 transition disabled:opacity-40">✏️ Editar</button>
        {!direccion.es_principal && (
          <button onClick={() => onMarcarPrincipal(direccion)} disabled={cargando}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-100 dark:bg-blue-900/40 hover:bg-blue-200 dark:hover:bg-blue-900/60 text-blue-700 dark:text-blue-300 transition disabled:opacity-40">
            {cargando ? 'Procesando...' : '⭐ Marcar como principal'}
          </button>
        )}
        <button onClick={() => onEliminar(direccion)} disabled={cargando}
          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-100 dark:bg-red-900/40 hover:bg-red-200 dark:hover:bg-red-900/60 text-red-700 dark:text-red-300 transition disabled:opacity-40">🗑️ Eliminar</button>
      </div>
    </div>
  )
}

export default function DireccionesPage() {
  const { direcciones, loading, eliminar, marcarPrincipal, recargar } = useDirecciones()
  const { toasts, addToast, removeToast } = useToast()
  const [modalAbierto, setModalAbierto]       = useState(false)
  const [direccionEditar, setDireccionEditar] = useState<Direccion | null>(null)
  const [loadingId, setLoadingId]             = useState<number | null>(null)

  const abrirCrear  = () => { setDireccionEditar(null); setModalAbierto(true) }
  const abrirEditar = (d: Direccion) => { setDireccionEditar(d); setModalAbierto(true) }
  const cerrarModal = () => { setModalAbierto(false); setDireccionEditar(null) }

  const handleMarcarPrincipal = async (d: Direccion) => {
    setLoadingId(d.id)
    try { await marcarPrincipal(d.id); addToast(`"${d.alias || d.linea1}" marcada como principal.`, 'success') }
    catch (e) { addToast(e instanceof ApiError ? e.message : 'Error al marcar como principal.', 'error') }
    finally { setLoadingId(null) }
  }

  const handleEliminar = async (d: Direccion) => {
    if (!confirm(`¿Eliminar la dirección "${d.alias || d.linea1}"?`)) return
    setLoadingId(d.id)
    try { await eliminar(d.id); addToast('Dirección eliminada.', 'success') }
    catch (e) { addToast(e instanceof ApiError ? e.message : 'Error al eliminar.', 'error') }
    finally { setLoadingId(null) }
  }

  const activas = direcciones

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Toast toasts={toasts} onRemove={removeToast} />
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">📍 Mis Direcciones</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{activas.length} dirección{activas.length !== 1 ? 'es' : ''} guardada{activas.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => recargar()} className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-xl text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition">🔄</button>
          <button onClick={abrirCrear} className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-xl text-sm font-semibold transition shadow-sm">
            <span className="text-lg leading-none">+</span> Nueva dirección
          </button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2].map(i => <div key={i} className="h-36 bg-gray-100 dark:bg-gray-700 rounded-2xl animate-pulse" />)}
        </div>
      ) : activas.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 py-16 text-center shadow-sm">
          <p className="text-4xl mb-3">🏠</p>
          <p className="font-semibold text-gray-700 dark:text-gray-200">Sin direcciones guardadas</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Agregá una dirección para facilitar la creación de pedidos.</p>
          <button onClick={abrirCrear} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 transition">Agregar primera dirección</button>
        </div>
      ) : (
        <div className="space-y-4">
          {activas.map(d => <DireccionCard key={d.id} direccion={d} onEditar={abrirEditar} onEliminar={handleEliminar} onMarcarPrincipal={handleMarcarPrincipal} loadingId={loadingId} />)}
        </div>
      )}

      <Modal open={modalAbierto} title={direccionEditar ? 'Editar dirección' : 'Nueva dirección'} onClose={cerrarModal} size="md">
        <DireccionForm direccion={direccionEditar} onSuccess={() => { cerrarModal(); addToast(direccionEditar ? 'Dirección actualizada.' : 'Dirección agregada.', 'success') }} onClose={cerrarModal} />
      </Modal>
    </div>
  )
}
