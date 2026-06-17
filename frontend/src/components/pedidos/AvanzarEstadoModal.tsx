// src/components/pedidos/AvanzarEstadoModal.tsx
import { useState } from 'react'
import type { Pedido, EstadoPedido } from '../../models/pedido'
import { getTransicionesValidas, ESTADO_LABELS, ESTADO_ICONOS, ESTADO_COLORES, ESTADOS_TERMINALES } from '../../models/pedido'
import type { RolCodigo } from '../../models/auth'
import { usePedidos } from '../../hooks/usePedidos'
import { ApiError } from '../../api/client'

interface Props { pedido: Pedido; roles: RolCodigo[]; usuarioId: number | null; onClose: () => void; onSuccess: (p: Pedido) => void }

export default function AvanzarEstadoModal({ pedido, roles, usuarioId, onClose, onSuccess }: Props) {
  const { avanzarEstado } = usePedidos()
  const esOwner = pedido.usuario_id === usuarioId
  const transiciones = getTransicionesValidas(pedido.estado_codigo, roles, esOwner)

  const [estadoHacia, setEstadoHacia] = useState<EstadoPedido | ''>(transiciones.length === 1 ? transiciones[0] : '')
  const [motivo, setMotivo]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  const requiereMotivo = estadoHacia === 'CANCELADO' || estadoHacia === 'CONFIRMADO'

  const handleSubmit = async () => {
    if (!estadoHacia) return
    if (requiereMotivo && !motivo.trim()) { setError('El motivo es requerido para esta transición.'); return }
    setLoading(true); setError('')
    try {
      await avanzarEstado(pedido.id, { estado_hacia: estadoHacia as EstadoPedido, motivo: motivo.trim() || null })
      onSuccess({ ...pedido, estado_codigo: estadoHacia as EstadoPedido }); onClose()
    } catch (e) { setError(e instanceof ApiError ? e.message : 'Error al avanzar el estado.') }
    finally { setLoading(false) }
  }

  const overlay = "fixed inset-0 z-50 flex items-center justify-center p-4"
  const backdropStyle = { backgroundColor: 'rgba(0,0,0,0.6)' }

  if (ESTADOS_TERMINALES.includes(pedido.estado_codigo)) {
    return (
      <div className={overlay} style={backdropStyle} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-sm p-6 text-center">
          <p className="text-4xl mb-3">{ESTADO_ICONOS[pedido.estado_codigo]}</p>
          <p className="font-semibold text-gray-700 dark:text-gray-200">Este pedido está en estado <strong>{ESTADO_LABELS[pedido.estado_codigo]}</strong> (terminal).</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">No admite más transiciones.</p>
          <button onClick={onClose} className="mt-4 px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium transition">Cerrar</button>
        </div>
      </div>
    )
  }

  if (transiciones.length === 0) {
    return (
      <div className={overlay} style={backdropStyle} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-sm p-6 text-center">
          <p className="text-3xl mb-3">🔒</p>
          <p className="font-semibold text-gray-700 dark:text-gray-200">Sin permisos</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Tu rol no permite avanzar el estado de este pedido desde <strong>{ESTADO_LABELS[pedido.estado_codigo]}</strong>.</p>
          <button onClick={onClose} className="mt-4 px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg text-sm font-medium transition">Cerrar</button>
        </div>
      </div>
    )
  }

  return (
    <div className={overlay} style={backdropStyle} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100">Avanzar Estado</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Pedido <strong>{pedido.codigo}</strong></p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <div className="p-6 space-y-5">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">Estado actual:</span>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${ESTADO_COLORES[pedido.estado_codigo]}`}>
              {ESTADO_ICONOS[pedido.estado_codigo]} {ESTADO_LABELS[pedido.estado_codigo]}
            </span>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Avanzar a:</p>
            <div className="space-y-2">
              {transiciones.map(t => (
                <label key={t} className={`flex items-center gap-3 p-3 rounded-xl border-2 cursor-pointer transition ${
                  estadoHacia === t ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                }`}>
                  <input type="radio" name="estado_hacia" value={t} checked={estadoHacia === t} onChange={() => { setEstadoHacia(t); setError('') }} className="accent-blue-600" />
                  <span className="text-lg">{ESTADO_ICONOS[t]}</span>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${ESTADO_COLORES[t]}`}>{ESTADO_LABELS[t]}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
              Motivo {requiereMotivo ? <span className="text-red-500">*</span> : <span className="text-gray-400 dark:text-gray-500">(opcional)</span>}
            </label>
            <textarea value={motivo} onChange={e => { setMotivo(e.target.value); setError('') }} rows={3}
              placeholder={estadoHacia === 'CANCELADO' ? 'Motivo de cancelación...' : 'Notas adicionales...'}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500" />
          </div>

          {error && <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-xl px-4 py-3 text-sm text-red-700 dark:text-red-300">{error}</div>}
        </div>

        <div className="flex gap-3 px-6 pb-6">
          <button onClick={onClose} className="flex-1 px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition">Cancelar</button>
          <button onClick={handleSubmit} disabled={!estadoHacia || loading}
            className="flex-1 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl text-sm font-semibold text-white transition">
            {loading ? 'Procesando...' : 'Confirmar'}
          </button>
        </div>
      </div>
    </div>
  )
}
