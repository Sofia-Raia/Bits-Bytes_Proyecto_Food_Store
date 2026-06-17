// src/components/estadisticas/PedidosEstadoPieChart.tsx
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { PedidosEstadoItem } from '../../models/estadistica'

interface Props { data: PedidosEstadoItem[] }

const COLORES: Record<string, string> = {
  PENDIENTE:  '#f59e0b',
  CONFIRMADO: '#3b82f6',
  EN_PREP:    '#8b5cf6',
  ENTREGADO:  '#22c55e',
  CANCELADO:  '#ef4444',
}

export default function PedidosEstadoPieChart({ data }: Props) {
  if (!data.length) return <p className="text-sm text-gray-400 italic">Sin datos.</p>
  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie data={data} dataKey="cantidad" nameKey="estado_codigo" cx="50%" cy="50%" outerRadius={90} label={({ estado_codigo, percent }) => `${estado_codigo} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
          {data.map(e => <Cell key={e.estado_codigo} fill={COLORES[e.estado_codigo] ?? '#6b7280'} />)}
        </Pie>
        <Tooltip formatter={(val, name) => [val, name]} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}
