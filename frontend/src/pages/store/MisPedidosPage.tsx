// src/pages/store/MisPedidosPage.tsx
import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getPedidosApi } from '../../api/pedidos'
import type { Pedido, EstadoPedido } from '../../models/pedido'
import { ESTADO_LABELS, ESTADO_COLORES, ESTADO_ICONOS, ESTADOS_TERMINALES } from '../../models/pedido'
import Pagination from '../../components/ui/Pagination'
import Modal from '../../components/ui/Modal'
import PedidoForm from '../../components/pedidos/PedidoForm'
import Toast, { useToast } from '../../components/ui/Toast'
import { useAuth } from '../../store/authStore'
import type { RolCodigo } from '../../models/auth'
import { useOrdersRealtime, useOrderSubscriptions } from '../../store/wsStore'
import { qk } from '../../queries/keys'

const PAGE_SIZE = 10

function formatFecha(iso: string) {
  return new Date(iso).toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatPrecio(n: number) {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)
}

function BadgeEstado({ estado }: { estado: EstadoPedido }) {
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full border ${ESTADO_COLORES[estado]}`}>
      {ESTADO_ICONOS[estado]} {ESTADO_LABELS[estado]}
    </span>
  )
}

export default function MisPedidosPage() {
  const qc = useQueryClient()
  const { user }   = useAuth()
  const roles      = (user?.roles ?? []) as RolCodigo[]
  const userId     = user?.id ?? null

  const [page, setPage] = useState(1)

  // Modal editar pedido PENDIENTE (T4)
  const [pedidoEditar, setPedidoEditar] = useState<Pedido | null>(null)
  const { toasts, addToast, removeToast } = useToast()

  const pedidosQuery = useQuery({
    queryKey: qk.pedidos.mis(page),
    queryFn: () => getPedidosApi(page, PAGE_SIZE),
    enabled: !!user,
  })

  const pedidos: Pedido[] = pedidosQuery.data?.items ?? []
  const total = pedidosQuery.data?.total ?? 0
  const loading = pedidosQuery.isLoading
  const error = pedidosQuery.error ? 'Error al cargar tus pedidos.' : ''
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // ── Parte 3: WebSocket — actualización en vivo de los pedidos del cliente ──
  // La conexión se mantiene mientras la página está montada y los eventos
  // invalidan el dominio "pedidos" desde el wsStore. Además se sigue cada pedido
  // activo (no terminal) por su room order:{id}.
  useOrdersRealtime(true)
  const idsActivos = useMemo(
    () => pedidos.filter(p => !ESTADOS_TERMINALES.includes(p.estado_codigo)).map(p => p.id),
    [pedidos],
  )
  useOrderSubscriptions(idsActivos)

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Toast toasts={toasts} onRemove={removeToast} />

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">📋 Mis Pedidos</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-0.5">Historial de tus compras</p>
        </div>
        <Link to="/store" className="text-sm text-blue-600 dark:text-blue-400 hover:underline font-medium">
          🛍️ Ir a la tienda
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-xl p-4 text-red-700 dark:text-red-300 text-sm mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 dark:bg-gray-700 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : pedidos.length === 0 ? (
        <div className="text-center py-16 text-gray-400 dark:text-gray-500">
          <p className="text-5xl mb-4">📭</p>
          <p className="font-semibold text-lg">Aún no tenés pedidos</p>
          <Link to="/store" className="mt-4 inline-block text-blue-600 dark:text-blue-400 hover:underline text-sm">
            Explorá la tienda
          </Link>
        </div>
      ) : (
        <>
          <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-100 dark:border-gray-700">
                <tr>
                  <th className="text-left px-5 py-3.5 font-semibold text-gray-600 dark:text-gray-300">Código</th>
                  <th className="text-left px-4 py-3.5 font-semibold text-gray-600 dark:text-gray-300">Estado</th>
                  <th className="text-right px-4 py-3.5 font-semibold text-gray-600 dark:text-gray-300">Total</th>
                  <th className="text-left px-4 py-3.5 font-semibold text-gray-600 dark:text-gray-300">Fecha</th>
                  <th className="px-4 py-3.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
                {pedidos.map(p => (
                  <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition">
                    <td className="px-5 py-3.5">
                      <Link to={`/pedidos/${p.id}`}
                        className="font-mono font-semibold text-blue-600 dark:text-blue-400 hover:underline">
                        {p.codigo}
                      </Link>
                    </td>
                    <td className="px-4 py-3.5">
                      <BadgeEstado estado={p.estado_codigo} />
                    </td>
                    <td className="px-4 py-3.5 text-right font-semibold text-gray-800 dark:text-gray-100">
                      {formatPrecio(p.total)}
                    </td>
                    <td className="px-4 py-4 text-gray-500 dark:text-gray-400 text-xs whitespace-nowrap">
                      {formatFecha(p.created_at)}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      {/* Editar visible solo si PENDIENTE y el pedido es propio (T4) */}
                      {p.estado_codigo === 'PENDIENTE' && p.usuario_id === userId && (
                        <button
                          onClick={() => setPedidoEditar(p)}
                          className="text-xs font-medium px-3 py-1.5 rounded-lg bg-amber-100 dark:bg-amber-900/40 hover:bg-amber-200 dark:hover:bg-amber-900/60 text-amber-700 dark:text-amber-300 transition"
                        >
                          ✏️ Editar
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4">
            <Pagination page={page} totalPages={totalPages} total={total} pageSize={PAGE_SIZE} onPage={setPage} loading={loading} />
          </div>
        </>
      )}

      {/* Modal editar pedido PENDIENTE */}
      <Modal
        open={!!pedidoEditar}
        title={`✏️ Editar pedido — ${pedidoEditar?.codigo ?? ''}`}
        onClose={() => setPedidoEditar(null)}
        size="lg"
      >
        {pedidoEditar && (
          <PedidoForm
            roles={roles}
            usuarioIdActual={userId}
            initial={pedidoEditar}
            onSuccess={() => {
              setPedidoEditar(null)
              addToast('Pedido actualizado ✅', 'success')
              qc.invalidateQueries({ queryKey: qk.pedidos.all })
            }}
            onClose={() => setPedidoEditar(null)}
          />
        )}
      </Modal>
    </div>
  )
}
