// src/pages/pedidos/PedidosPage.tsx
import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { usePedidos } from '../../hooks/usePedidos'
import { useAuth } from '../../store/authStore'
import type { Pedido, EstadoPedido, HistorialEntrada } from '../../models/pedido'
import {
  ESTADO_LABELS, ESTADO_COLORES, ESTADO_ICONOS,
  ESTADOS_TERMINALES,
} from '../../models/pedido'
import type { RolCodigo } from '../../models/auth'
import Modal from '../../components/ui/Modal'
import Pagination from '../../components/ui/Pagination'
import Toast, { useToast } from '../../components/ui/Toast'
import PedidoForm from '../../components/pedidos/PedidoForm'
import PedidoTimeline from '../../components/pedidos/PedidoTimeline'
import AvanzarEstadoModal from '../../components/pedidos/AvanzarEstadoModal'
import { PedidosBoard } from '../../components/pedidos/PedidosBoard'
import { useOrdersRealtime } from '../../store/wsStore'
import { ApiError } from '../../api/client'

const ESTADOS: EstadoPedido[] = ['PENDIENTE', 'CONFIRMADO', 'EN_PREP', 'ENTREGADO', 'CANCELADO']

function formatFecha(iso: string) {
  return new Date(iso).toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatDireccionSnapshot(raw: string | null): string | null {
  if (!raw) return null
  try {
    const d = JSON.parse(raw) as {
      alias?: string | null; linea1?: string; linea2?: string | null
      ciudad?: string; provincia?: string | null; codigo_postal?: string | null
    }
    const partes = [d.alias, d.linea1, d.linea2, d.ciudad, d.provincia].filter(Boolean)
    return partes.join(', ') + (d.codigo_postal ? ` (CP ${d.codigo_postal})` : '')
  } catch {
    return raw
  }
}

function BadgeEstado({ estado }: { estado: EstadoPedido }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border ${ESTADO_COLORES[estado]}`}>
      <span>{ESTADO_ICONOS[estado]}</span>
      {ESTADO_LABELS[estado]}
    </span>
  )
}

export default function PedidosPage() {
  const {
    pedidos, loading, total, page, pageSize, totalPages, setPage,
    filtroEstado, setFiltroEstado, busqueda, setBusqueda,
    eliminar, recargar,
  } = usePedidos()
  const { user } = useAuth()

  const roles      = (user?.roles ?? []) as RolCodigo[]
  const esAdmin    = roles.includes('ADMIN')
  const esPedidos  = roles.includes('PEDIDOS')
  const esClient   = roles.length === 1 && roles.includes('CLIENT')
  const puedeEditarCualquiera = esAdmin || esPedidos

 
  const [viewMode, setViewMode] = useState<'tabla' | 'board'>('board')

  
  // La sincronización llega por invalidación de queries desde el wsStore; aquí
  // sólo se gestiona el ciclo de vida de la conexión. STOCK no se conecta.
  useOrdersRealtime(esClient ? true : (esAdmin || esPedidos))

  const { toasts, addToast, removeToast } = useToast()

  const [modalCrear, setModalCrear]       = useState(false)
  const [pedidoDetalle, setPedidoDetalle] = useState<Pedido | null>(null)
  const [pedidoAvanzar, setPedidoAvanzar] = useState<Pedido | null>(null)
  const [pedidoEditar, setPedidoEditar]   = useState<Pedido | null>(null)
  const [historial, setHistorial]         = useState<HistorialEntrada[]>([])

  const abrirDetalle = useCallback((p: Pedido) => {
    setPedidoDetalle(p)
    setHistorial(p.historial ?? [])
  }, [])

  const puedeEditar = (p: Pedido) =>
    p.estado_codigo === 'PENDIENTE' &&
    (puedeEditarCualquiera || (esClient && p.usuario_id === user?.id))

  const handleEliminar = async (p: Pedido) => {
    if (ESTADOS_TERMINALES.includes(p.estado_codigo) && p.estado_codigo === 'ENTREGADO') {
      addToast('No se puede eliminar un pedido entregado.', 'error')
      return
    }
    if (!confirm(`¿Eliminar pedido ${p.codigo}?`)) return
    try {
      await eliminar(p.id)
      addToast(`Pedido ${p.codigo} eliminado.`, 'success')
    } catch (e) {
      addToast(e instanceof ApiError ? e.message : 'Error al eliminar.', 'error')
    }
  }

  const usuarioIdActual = user?.id ?? null

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <Toast toasts={toasts} onRemove={removeToast} />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">📋 Pedidos</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {total} pedido{total !== 1 ? 's' : ''} en total
          </p>
        </div>
        {esClient ? (
          <Link
            to="/store"
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-xl text-sm font-semibold transition shadow-sm"
          >
            <span className="text-lg leading-none">+</span> Nuevo pedido
          </Link>
        ) : (
          <button
            onClick={() => setModalCrear(true)}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-xl text-sm font-semibold transition shadow-sm"
          >
            <span className="text-lg leading-none">+</span> Nuevo pedido
          </button>
        )}
      </div>

      {/* Filtros */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 mb-5 flex flex-col sm:flex-row gap-3">
        <input
          type="text"
          value={busqueda}
          onChange={e => setBusqueda(e.target.value)}
          placeholder="Buscar por código..."
          className="flex-1 border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
        />
        <select
          value={filtroEstado}
          onChange={e => setFiltroEstado(e.target.value as EstadoPedido | '')}
          className="border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-44 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100"
        >
          <option value="">Todos los estados</option>
          {ESTADOS.map(e => (
            <option key={e} value={e}>{ESTADO_ICONOS[e]} {ESTADO_LABELS[e]}</option>
          ))}
        </select>
        <button
          onClick={() => recargar()}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-xl text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
        >
          🔄 Actualizar
        </button>

        {/* Toggle Tabla / Board (Parte 3) */}
        <div className="inline-flex rounded-xl border border-gray-300 dark:border-gray-600 overflow-hidden self-start">
          <button
            onClick={() => setViewMode('tabla')}
            className={`px-4 py-2 text-sm font-medium transition ${
              viewMode === 'tabla'
                ? 'bg-blue-600 text-white'
                : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'
            }`}
          >
            ☰ Tabla
          </button>
          <button
            onClick={() => setViewMode('board')}
            className={`px-4 py-2 text-sm font-medium transition ${
              viewMode === 'board'
                ? 'bg-blue-600 text-white'
                : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'
            }`}
          >
            ▦ Board
          </button>
        </div>
      </div>

      {/* Vista Board (kanban)*/}
      {viewMode === 'board' ? (
        <PedidosBoard
          pedidos={pedidos}
          roles={roles}
          onAvanzar={(p) => setPedidoAvanzar(p as Pedido)}
        />
      ) : (
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
        {loading ? (
          <div className="p-8 space-y-3">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-12 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : pedidos.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-4xl mb-3">📭</p>
            <p className="text-gray-500 dark:text-gray-400 font-medium">No hay pedidos{filtroEstado ? ` con estado "${ESTADO_LABELS[filtroEstado]}"` : ''}.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-100 dark:border-gray-700">
                <tr>
                  <th className="text-left px-5 py-3.5 font-semibold text-gray-600 dark:text-gray-300">Código</th>
                  <th className="text-left px-4 py-3.5 font-semibold text-gray-600 dark:text-gray-300">Estado</th>
                  {!esClient && (
                    <th className="text-left px-4 py-3.5 font-semibold text-gray-600 dark:text-gray-300">Usuario ID</th>
                  )}
                  <th className="text-right px-4 py-3.5 font-semibold text-gray-600 dark:text-gray-300">Total</th>
                  <th className="text-left px-4 py-3.5 font-semibold text-gray-600 dark:text-gray-300">Fecha</th>
                  <th className="px-4 py-3.5 font-semibold text-gray-600 dark:text-gray-300 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
                {pedidos.map(p => (
                  <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/40 transition">
                    <td className="px-5 py-3.5">
                      <Link to={`/pedidos/${p.id}`} className="font-mono font-semibold text-blue-600 dark:text-blue-400 hover:underline">{p.codigo}</Link>
                    </td>
                    <td className="px-4 py-3.5">
                      <BadgeEstado estado={p.estado_codigo} />
                    </td>
                    {!esClient && (
                      <td className="px-4 py-3.5 text-gray-500 dark:text-gray-400 text-xs">#{p.usuario_id}{p.usuario_nombre ? ` · ${p.usuario_nombre}` : ''}</td>
                    )}
                    <td className="px-4 py-3.5 text-right font-semibold text-gray-800 dark:text-gray-200">
                      ${p.total.toFixed(2)}
                    </td>
                    <td className="px-4 py-3.5 text-gray-500 dark:text-gray-400 text-xs whitespace-nowrap">
                      {formatFecha(p.created_at)}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => abrirDetalle(p)}
                          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 transition"
                        >
                          👁 Ver
                        </button>
                        {!esClient && !ESTADOS_TERMINALES.includes(p.estado_codigo) && (
                          <button
                            onClick={() => setPedidoAvanzar(p)}
                            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-100 dark:bg-blue-900/40 hover:bg-blue-200 dark:hover:bg-blue-900/60 text-blue-700 dark:text-blue-300 transition"
                          >
                            ⚡ Avanzar
                          </button>
                        )}
                        {puedeEditar(p) && (
                          <button
                            onClick={() => setPedidoEditar(p)}
                            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-100 dark:bg-amber-900/40 hover:bg-amber-200 dark:hover:bg-amber-900/60 text-amber-700 dark:text-amber-300 transition"
                          >
                            ✏️ Editar
                          </button>
                        )}
                        {esAdmin && (
                          <button
                            onClick={() => handleEliminar(p)}
                            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-100 dark:bg-red-900/40 hover:bg-red-200 dark:hover:bg-red-900/60 text-red-700 dark:text-red-300 transition"
                          >
                            🗑
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && pedidos.length > 0 && (
          <div className="px-5 pb-4">
            <Pagination page={page} totalPages={totalPages} total={total} pageSize={pageSize} onPage={setPage} loading={loading} />
          </div>
        )}
      </div>
      )}

      {/* Modal Crear Pedido */}
      <Modal open={modalCrear} title="Nuevo pedido" onClose={() => setModalCrear(false)} size="lg">
        <PedidoForm
          roles={roles}
          usuarioIdActual={usuarioIdActual}
          onSuccess={() => { setModalCrear(false); addToast('Pedido creado exitosamente. 🎉', 'success') }}
          onClose={() => setModalCrear(false)}
        />
      </Modal>

      {/* Modal Editar pedido PENDIENTE  */}
      <Modal
        open={!!pedidoEditar}
        title={`✏️ Editar pedido — ${pedidoEditar?.codigo ?? ''}`}
        onClose={() => setPedidoEditar(null)}
        size="lg"
      >
        {pedidoEditar && (
          <PedidoForm
            roles={roles}
            usuarioIdActual={usuarioIdActual}
            initial={pedidoEditar}
            onSuccess={() => {
              setPedidoEditar(null)
              addToast('Pedido actualizado exitosamente. ✅', 'success')
              recargar()
            }}
            onClose={() => setPedidoEditar(null)}
          />
        )}
      </Modal>

      {/* Modal Detalle + Historial */}
      {pedidoDetalle && (
        <Modal
          open={!!pedidoDetalle}
          title={`Detalle — ${pedidoDetalle.codigo}`}
          onClose={() => setPedidoDetalle(null)}
          size="lg"
        >
          <div className="space-y-6">
            {/* Info general */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-gray-500 dark:text-gray-400 text-xs mb-1">Estado</p>
                <BadgeEstado estado={pedidoDetalle.estado_codigo} />
              </div>
              <div>
                <p className="text-gray-500 dark:text-gray-400 text-xs mb-1">Forma de pago</p>
                <p className="font-medium text-gray-800 dark:text-gray-200">{pedidoDetalle.forma_pago_codigo}</p>
              </div>
              <div>
                <p className="text-gray-500 dark:text-gray-400 text-xs mb-1">Fecha</p>
                <p className="font-medium text-gray-800 dark:text-gray-200">{formatFecha(pedidoDetalle.created_at)}</p>
              </div>
              {pedidoDetalle.direccion_snapshot && (
                <div className="col-span-2 sm:col-span-3">
                  <p className="text-gray-500 dark:text-gray-400 text-xs mb-1">Dirección de entrega</p>
                  <p className="font-medium text-xs text-gray-800 dark:text-gray-200">{formatDireccionSnapshot(pedidoDetalle.direccion_snapshot)}</p>
                </div>
              )}
              {pedidoDetalle.notas && (
                <div className="col-span-2 sm:col-span-3">
                  <p className="text-gray-500 dark:text-gray-400 text-xs mb-1">Notas</p>
                  <p className="text-gray-700 dark:text-gray-300 text-xs">{pedidoDetalle.notas}</p>
                </div>
              )}
            </div>

            {/* Items */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">Items</h3>
              <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-700/50">
                    <tr>
                      <th className="text-left px-4 py-2.5 text-gray-600 dark:text-gray-300 font-medium">Producto</th>
                      <th className="text-right px-3 py-2.5 text-gray-600 dark:text-gray-300 font-medium">Precio</th>
                      <th className="text-center px-3 py-2.5 text-gray-600 dark:text-gray-300 font-medium">Cant.</th>
                      <th className="text-right px-3 py-2.5 text-gray-600 dark:text-gray-300 font-medium">Subtotal</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {(pedidoDetalle.detalles ?? []).map(d => (
                      <tr key={`${d.pedido_id}-${d.producto_id}`}>
                        <td className="px-4 py-2.5 font-medium text-gray-800 dark:text-gray-200">{d.nombre_snapshot}</td>
                        <td className="px-3 py-2.5 text-right text-gray-600 dark:text-gray-400">${d.precio_snapshot.toFixed(2)}</td>
                        <td className="px-3 py-2.5 text-center text-gray-600 dark:text-gray-400">{d.cantidad}</td>
                        <td className="px-3 py-2.5 text-right font-semibold text-gray-800 dark:text-gray-200">${d.subtotal_snap.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Totales */}
              <div className="mt-3 bg-gray-50 dark:bg-gray-700/40 rounded-xl p-4 space-y-1.5 text-sm">
                <div className="flex justify-between text-gray-600 dark:text-gray-400">
                  <span>Subtotal</span><span>${pedidoDetalle.subtotal.toFixed(2)}</span>
                </div>
                {pedidoDetalle.descuento > 0 && (
                  <div className="flex justify-between text-green-600 dark:text-green-400">
                    <span>Descuento</span><span>-${pedidoDetalle.descuento.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between text-gray-600 dark:text-gray-400">
                  <span>Envío</span>
                  <span>{pedidoDetalle.costo_envio > 0 ? `$${pedidoDetalle.costo_envio.toFixed(2)}` : 'Gratis'}</span>
                </div>
                <div className="flex justify-between font-bold text-gray-800 dark:text-gray-100 pt-1 border-t border-gray-200 dark:border-gray-600">
                  <span>Total</span><span>${pedidoDetalle.total.toFixed(2)}</span>
                </div>
              </div>
            </div>

            {/* Historial */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">Historial de estados</h3>
                {!esClient && !ESTADOS_TERMINALES.includes(pedidoDetalle.estado_codigo) && (
                  <button
                    onClick={() => { setPedidoAvanzar(pedidoDetalle); setPedidoDetalle(null) }}
                    className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
                  >
                    ⚡ Avanzar estado
                  </button>
                )}
              </div>
              <PedidoTimeline historial={historial} />
            </div>
          </div>
        </Modal>
      )}

      {/* Modal Avanzar Estado */}
      {pedidoAvanzar && (
        <AvanzarEstadoModal
          pedido={pedidoAvanzar}
          roles={roles}
          usuarioId={usuarioIdActual}
          onClose={() => setPedidoAvanzar(null)}
          onSuccess={pedidoActualizado => {
            addToast(`Pedido ${pedidoActualizado.codigo} → ${ESTADO_LABELS[pedidoActualizado.estado_codigo]}`, 'success')
            setPedidoAvanzar(null)
          }}
        />
      )}
    </div>
  )
}
