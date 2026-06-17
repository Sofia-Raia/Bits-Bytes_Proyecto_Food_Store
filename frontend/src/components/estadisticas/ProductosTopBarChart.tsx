// src/components/estadisticas/ProductosTopBarChart.tsx
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import type { ProductoTopItem } from '../../models/estadistica'

interface Props { data: ProductoTopItem[] }

const fmt = (n: number) =>
  n.toLocaleString('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 })

const COLORES = ['#3b82f6','#8b5cf6','#f59e0b','#22c55e','#ef4444','#06b6d4','#ec4899','#84cc16','#f97316','#6366f1']

export default function ProductosTopBarChart({ data }: Props) {
  if (!data.length) return <p className="text-sm text-gray-400 italic">Sin datos.</p>
  const mapped = data.map(d => ({ ...d, nombre_corto: d.nombre.length > 18 ? d.nombre.slice(0, 16) + '…' : d.nombre }))
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={mapped} layout="vertical" margin={{ left: 10, right: 20 }}>
        <XAxis type="number" tickFormatter={fmt} tick={{ fontSize: 11 }} width={80} />
        <YAxis type="category" dataKey="nombre_corto" tick={{ fontSize: 11 }} width={130} />
        <Tooltip
          formatter={(val, _name, props) => [
            `${fmt(Number(val))} · ${props.payload.cantidad_vendida} u.`,
            'Ingresos',
          ]}
        />
        <Bar dataKey="ingresos" radius={[0, 6, 6, 0]}>
          {mapped.map((_e, i) => <Cell key={i} fill={COLORES[i % COLORES.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
