// src/pages/pedidos/PedidoDetallePage.tsx
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getPedidoApi } from '../../api/pedidos'
import { qk } from '../../queries/keys'
import type { Pedido, EstadoPedido, HistorialEntrada } from '../../models/pedido'
import { ESTADO_LABELS, ESTADO_COLORES, ESTADO_ICONOS } from '../../models/pedido'
import PedidoTimeline from '../../components/pedidos/PedidoTimeline'
import PagarMercadoPago from '../../components/pagos/PagarMercadoPago'

function formatPrecio(n: number) {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)
}

function formatFecha(iso: string) {
  return new Date(iso).toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function BadgeEstado({ estado }: { estado: EstadoPedido }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-1 rounded-full border ${ESTADO_COLORES[estado]}`}>
      {ESTADO_ICONOS[estado]} {ESTADO_LABELS[estado]}
    </span>
  )
}

interface DireccionSnapshot {
  alias?: string | null
  linea1?: string
  linea2?: string | null
  ciudad?: string
  provincia?: string | null
  codigo_postal?: string | null
}

function parseSnapshot(raw: string | null): DireccionSnapshot | null {
  if (!raw) return null
  try { return JSON.parse(raw) as DireccionSnapshot } catch { return null }
}

export default function PedidoDetallePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const pedidoQuery = useQuery({
    queryKey: qk.pedidos.detail(Number(id)),
    queryFn: () => getPedidoApi(Number(id)),
    enabled: !!id,
  })

  const pedido = pedidoQuery.data ?? null
  const historial: HistorialEntrada[] = pedido?.historial ?? []
  const loading = pedidoQuery.isLoading
  const error = pedidoQuery.error
    ? (pedidoQuery.error instanceof Error ? pedidoQuery.error.message : 'No se pudo cargar el pedido.')
    : ''

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-10 animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
        <div className="h-40 bg-gray-100 dark:bg-gray-800 rounded-2xl" />
        <div className="h-60 bg-gray-100 dark:bg-gray-800 rounded-2xl" />
      </div>
    )
  }

  if (error || !pedido) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-10">
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-xl p-5 text-red-700 dark:text-red-300">
          {error || 'Pedido no encontrado.'}
        </div>
        <button onClick={() => navigate(-1)} className="mt-4 text-sm text-blue-600 dark:text-blue-400 hover:underline">
          ← Volver
        </button>
      </div>
    )
  }

  const snapshot = parseSnapshot(pedido.direccion_snapshot)

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="font-mono text-xl font-bold text-gray-800 dark:text-gray-100">{pedido.codigo}</span>
          <BadgeEstado estado={pedido.estado_codigo} />
        </div>
        <button onClick={() => navigate(-1)} className="text-sm text-blue-600 dark:text-blue-400 hover:underline font-medium">
          ← Volver
        </button>
      </div>

      {/* Pago con MercadoPago: solo si el pedido está PENDIENTE y la forma de pago es MERCADOPAGO */}
      {pedido.estado_codigo === 'PENDIENTE' && pedido.forma_pago_codigo === 'MERCADOPAGO' && (
        <div className="mb-6">
          <PagarMercadoPago pedidoId={pedido.id} />
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        {/* Info general */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-5 space-y-3 text-sm">
          <h2 className="font-semibold text-gray-700 dark:text-gray-200">ℹ️ Información del pedido</h2>
          <div className="flex justify-between text-gray-600 dark:text-gray-400">
            <span>Fecha</span>
            <span className="font-medium text-gray-800 dark:text-gray-200">{formatFecha(pedido.created_at)}</span>
          </div>
          <div className="flex justify-between text-gray-600 dark:text-gray-400">
            <span>Forma de pago</span>
            <span className="font-medium text-gray-800 dark:text-gray-200">{pedido.forma_pago_codigo}</span>
          </div>
          {snapshot && (
            <div className="text-gray-600 dark:text-gray-400">
              <span className="block mb-0.5">Dirección de entrega:</span>
              <span className="font-medium text-gray-800 dark:text-gray-200">
                {[snapshot.alias, snapshot.linea1, snapshot.linea2, snapshot.ciudad, snapshot.provincia]
                  .filter(Boolean)
                  .join(', ')}
                {snapshot.codigo_postal ? ` CP ${snapshot.codigo_postal}` : ''}
              </span>
            </div>
          )}
        </div>

        {/* Totales */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-5 space-y-2 text-sm">
          <h2 className="font-semibold text-gray-700 dark:text-gray-200">💰 Totales</h2>
          <div className="flex justify-between text-gray-600 dark:text-gray-400">
            <span>Subtotal</span>
            <span>{formatPrecio(pedido.subtotal)}</span>
          </div>
          <div className="flex justify-between text-gray-600 dark:text-gray-400">
            <span>Envío</span>
            <span>{pedido.costo_envio ? formatPrecio(pedido.costo_envio) : 'Sin cargo'}</span>
          </div>
          {pedido.descuento > 0 && (
            <div className="flex justify-between text-green-700 dark:text-green-400">
              <span>Descuento</span>
              <span>-{formatPrecio(pedido.descuento)}</span>
            </div>
          )}
          <div className="flex justify-between font-bold text-gray-800 dark:text-gray-100 text-base border-t border-gray-100 dark:border-gray-700 pt-2">
            <span>Total</span>
            <span className="text-blue-700 dark:text-blue-400">{formatPrecio(pedido.total)}</span>
          </div>
        </div>
      </div>

      {/* Detalle de productos */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm overflow-hidden mb-6">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700">
          <h2 className="font-semibold text-gray-700 dark:text-gray-200">🛒 Detalle de productos</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th className="text-left px-5 py-3 font-semibold text-gray-600 dark:text-gray-300">Producto</th>
              <th className="text-center px-4 py-3 font-semibold text-gray-600 dark:text-gray-300">Cant.</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-gray-300">Precio unit.</th>
              <th className="text-right px-5 py-3 font-semibold text-gray-600 dark:text-gray-300">Subtotal</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
            {pedido.detalles.map(d => (
              <tr key={d.producto_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/40 transition">
                <td className="px-5 py-3 text-gray-800 dark:text-gray-200 font-medium">{d.nombre_snapshot}</td>
                <td className="px-4 py-3 text-center text-gray-600 dark:text-gray-400">{d.cantidad}</td>
                <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-400">{formatPrecio(d.precio_snapshot)}</td>
                <td className="px-5 py-3 text-right font-semibold text-gray-800 dark:text-gray-200">{formatPrecio(d.subtotal_snap)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Timeline */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-5">
        <h2 className="font-semibold text-gray-700 dark:text-gray-200 mb-4">📋 Historial de estados</h2>
        <PedidoTimeline historial={historial} />
      </div>
    </div>
  )
}
