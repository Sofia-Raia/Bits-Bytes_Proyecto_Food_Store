// src/components/estadisticas/KpiCards.tsx
import type { ResumenResponse } from '../../models/estadistica'

const fmt = (n: number) =>
  n.toLocaleString('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 })

interface Props { data: ResumenResponse }

export default function KpiCards({ data }: Props) {
  const cards = [
    { label: 'Ventas hoy',       valor: fmt(data.ventas_hoy),       icon: '💰' },
    { label: 'Ventas del mes',   valor: fmt(data.ventas_mes),        icon: '📅' },
    { label: 'Ticket promedio',  valor: fmt(data.ticket_promedio),   icon: '🎟️' },
    { label: 'Pedidos activos',  valor: String(data.pedidos_activos), icon: '🔄' },
  ]
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map(c => (
        <div key={c.label} className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5">
          <p className="text-2xl mb-1">{c.icon}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">{c.label}</p>
          <p className="mt-1 text-xl font-semibold text-gray-900 dark:text-gray-50">{c.valor}</p>
        </div>
      ))}
    </div>
  )
}
