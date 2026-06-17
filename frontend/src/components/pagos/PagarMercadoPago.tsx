// src/components/pagos/PagarMercadoPago.tsx
import { usePagoStore } from '../../store/pagoStore'

interface Props {
  pedidoId: number
}

/**
 * Botón "Pagar con MercadoPago".
 * Crea la preferencia en el backend (vía pagoStore) y redirige al init_point de
 * Checkout Pro. Si no hay VITE_MP_PUBLIC_KEY configurada, muestra un aviso de
 * "MP no configurado".
 */
export default function PagarMercadoPago({ pedidoId }: Props) {
  const loading = usePagoStore(s => s.loading)
  const error = usePagoStore(s => s.error)
  const crearPreferencia = usePagoStore(s => s.crearPreferencia)

  const mpConfigurado = !!import.meta.env.VITE_MP_PUBLIC_KEY

  const handlePagar = async () => {
    const initPoint = await crearPreferencia(pedidoId)
    if (initPoint) {
      // Redirigir al checkout de MercadoPago
      window.location.href = initPoint
    }
  }

  if (!mpConfigurado) {
    return (
      <div className="rounded-xl border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/30 p-4 text-sm text-amber-800 dark:text-amber-300">
        MercadoPago no está configurado (falta VITE_MP_PUBLIC_KEY).
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={handlePagar}
        disabled={loading}
        className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-sky-500 hover:bg-sky-600 disabled:opacity-60 text-white font-semibold px-5 py-2.5 transition-colors"
      >
        {loading ? 'Redirigiendo a MercadoPago…' : 'Pagar con MercadoPago'}
      </button>
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  )
}
