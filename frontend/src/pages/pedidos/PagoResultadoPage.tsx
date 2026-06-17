// src/pages/pedidos/PagoResultadoPage.tsx
import { useEffect, useState } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { usePagoStore } from '../../store/pagoStore'
import type { PagoResultadoStatus } from '../../models/pago'

/**
 * Página de retorno de MercadoPago: /pedidos/:id/pago/:status (success|failure|pending).
 * Al montar, llama a confirmarPago (pagoStore) para refrescar el estado real del
 * pago (el webhook puede haber llegado antes o después que el redirect) e
 * invalidar el pedido afectado; luego muestra el resultado.
 */
export default function PagoResultadoPage() {
  const { id, status } = useParams<{ id: string; status: PagoResultadoStatus }>()
  const [searchParams] = useSearchParams()
  const [estado, setEstado] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const confirmarPago = usePagoStore(s => s.confirmarPago)

  const pedidoId = Number(id)
  const paymentIdRaw = searchParams.get('payment_id')
  const paymentId = paymentIdRaw ? Number(paymentIdRaw) : undefined

  useEffect(() => {
    let cancelled = false
    confirmarPago(pedidoId, paymentId)
      .then(() => {
        if (cancelled) return
        setEstado(usePagoStore.getState().estado)
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [pedidoId, paymentId, confirmarPago])

  const aprobado = estado === 'aprobado' || status === 'success'
  const rechazado = estado === 'rechazado' || status === 'failure'

  const titulo = aprobado
    ? '¡Pago aprobado!'
    : rechazado
      ? 'El pago no se completó'
      : 'Pago pendiente'

  const detalle = aprobado
    ? 'Tu pago fue acreditado y el pedido quedó confirmado.'
    : rechazado
      ? 'El pago fue rechazado o cancelado. Podés volver a intentarlo desde tus pedidos.'
      : 'Estamos esperando la confirmación del pago. Te avisaremos cuando se acredite.'

  const colorCard = aprobado
    ? 'border-green-200 dark:border-green-700 bg-green-50 dark:bg-green-900/30'
    : rechazado
      ? 'border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/30'
      : 'border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/30'

  return (
    <div className="max-w-xl mx-auto px-4 py-12">
      <div className={`rounded-2xl border p-6 ${colorCard}`}>
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-2">
          {loading ? 'Verificando el pago…' : titulo}
        </h1>
        {!loading && (
          <>
            <p className="text-gray-700 dark:text-gray-300 mb-1">{detalle}</p>
            {estado && (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Estado del pago: <span className="font-medium">{estado}</span>
              </p>
            )}
          </>
        )}
      </div>

      <div className="mt-6 flex gap-3">
        <Link
          to="/store/mis-pedidos"
          className="inline-flex items-center rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 transition-colors"
        >
          Ir a Mis pedidos
        </Link>
        <Link
          to={`/pedidos/${pedidoId}`}
          className="inline-flex items-center rounded-xl border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 font-medium px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          Ver pedido
        </Link>
      </div>
    </div>
  )
}
