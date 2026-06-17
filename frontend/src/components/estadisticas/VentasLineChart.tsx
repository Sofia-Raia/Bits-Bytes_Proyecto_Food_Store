// src/components/estadisticas/VentasLineChart.tsx
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import type { VentasPeriodoItem } from '../../models/estadistica'

interface Props { data: VentasPeriodoItem[] }

const fmt = (n: number) =>
  n.toLocaleString('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 })

export default function VentasLineChart({ data }: Props) {
  if (!data.length) return <p className="text-sm text-gray-400 italic">Sin datos para el período.</p>
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ left: 10, right: 10 }}>
        <XAxis dataKey="periodo" tick={{ fontSize: 11 }} />
        <YAxis yAxisId="left"  tickFormatter={fmt}   tick={{ fontSize: 11 }} width={90} />
        <YAxis yAxisId="right" orientation="right"   tick={{ fontSize: 11 }} allowDecimals={false} />
        <Tooltip formatter={(val, name) => name === 'total_ventas' ? fmt(Number(val)) : val} />
        <Legend />
        <Line yAxisId="left"  type="monotone" dataKey="total_ventas"    stroke="#3b82f6" strokeWidth={2} dot={false} name="Ventas ($)" />
        <Line yAxisId="right" type="monotone" dataKey="cantidad_pedidos" stroke="#22c55e" strokeWidth={2} dot={false} name="Pedidos" />
      </LineChart>
    </ResponsiveContainer>
  )
}
