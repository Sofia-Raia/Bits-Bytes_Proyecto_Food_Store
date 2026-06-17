// src/components/pedidos/PedidoTimeline.tsx
import type { HistorialEntrada } from '../../models/pedido'
import { ESTADO_LABELS, ESTADO_ICONOS, ESTADO_COLORES } from '../../models/pedido'

interface Props {
  historial: HistorialEntrada[]
  loading?: boolean
}

function formatFecha(iso: string): string {
  return new Date(iso).toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function PedidoTimeline({ historial, loading }: Props) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map(i => (
          <div key={i} className="flex gap-3 animate-pulse">
            <div className="w-9 h-9 rounded-full bg-gray-200 dark:bg-gray-700 shrink-0" />
            <div className="flex-1 space-y-1.5 pt-1">
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
              <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (!historial?.length) {
    return <p className="text-sm text-gray-400 dark:text-gray-500 italic">Sin historial disponible.</p>
  }

  return (
    <ol className="relative border-l-2 border-gray-200 dark:border-gray-700 ml-4 space-y-1">
      {historial.map((entrada, idx) => {
        const esUltimo = idx === historial.length - 1
        const color = ESTADO_COLORES[entrada.estado_hacia]
        const icono = ESTADO_ICONOS[entrada.estado_hacia]
        const label = ESTADO_LABELS[entrada.estado_hacia]

        return (
          <li key={entrada.id} className="ml-6 pb-5">
            <span
              className={`absolute -left-[1.1rem] flex items-center justify-center w-8 h-8 rounded-full border-2 border-white dark:border-gray-800 shadow text-sm ${
                esUltimo ? 'bg-blue-600 text-white' : 'bg-white dark:bg-gray-800'
              }`}
            >
              {icono}
            </span>

            <div className={`ml-1 rounded-xl border px-4 py-3 ${color}`}>
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <span className="font-semibold text-sm">{label}</span>
                <time className="text-xs opacity-70">{formatFecha(entrada.created_at)}</time>
              </div>
              {entrada.estado_desde && (
                <p className="text-xs opacity-60 mt-0.5">
                  Desde: {ESTADO_LABELS[entrada.estado_desde]}
                </p>
              )}
              {entrada.motivo && (
                <p className="text-xs mt-1 font-medium">
                  Motivo: <span className="font-normal">{entrada.motivo}</span>
                </p>
              )}
              {entrada.usuario_id && (
                <p className="text-xs opacity-60 mt-0.5">
                  Usuario ID: {entrada.usuario_id}
                </p>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
