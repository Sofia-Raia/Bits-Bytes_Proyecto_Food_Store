// src/pages/estadisticas/EstadisticasPage.tsx
import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../../store/authStore'
import { hasAnyRole } from '../../models/auth'
import {
  useResumen, useVentas, useProductosTop, usePedidosPorEstado, useIngresos,
} from '../../hooks/useEstadisticas'
import KpiCards from '../../components/estadisticas/KpiCards'
import VentasLineChart from '../../components/estadisticas/VentasLineChart'
import ProductosTopBarChart from '../../components/estadisticas/ProductosTopBarChart'
import PedidosEstadoPieChart from '../../components/estadisticas/PedidosEstadoPieChart'
import IngresosFormaPagoChart from '../../components/estadisticas/IngresosFormaPagoChart'

type Agrupacion = 'day' | 'week' | 'month'

function hoy() { return new Date().toISOString().slice(0, 10) }
function hace(dias: number) {
  const d = new Date(); d.setDate(d.getDate() - dias); return d.toISOString().slice(0, 10)
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5">
      <h2 className="text-base font-semibold text-gray-800 dark:text-gray-100 mb-4">{title}</h2>
      {children}
    </div>
  )
}

export default function EstadisticasPage() {
  const { user } = useAuth()
  if (!hasAnyRole(user, ['ADMIN'])) return <Navigate to="/pedidos" replace />

  const [desde, setDesde] = useState(hace(29))
  const [hasta, setHasta] = useState(hoy())
  const [agrupacion, setAgrupacion] = useState<Agrupacion>('day')

  const resumenQ        = useResumen()
  const ventasQ         = useVentas(desde, hasta, agrupacion)
  const productosTopQ   = useProductosTop(10)
  const pedidosEstadoQ  = usePedidosPorEstado()
  const ingresosQ       = useIngresos(desde, hasta)

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">📊 Estadísticas</h1>
        <div className="flex flex-wrap gap-2 items-center text-sm">
          <input type="date" value={desde} onChange={e => setDesde(e.target.value)}
            className="border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200" />
          <span className="text-gray-400">→</span>
          <input type="date" value={hasta} onChange={e => setHasta(e.target.value)}
            className="border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200" />
          <select value={agrupacion} onChange={e => setAgrupacion(e.target.value as Agrupacion)}
            className="border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200">
            <option value="day">Por día</option>
            <option value="week">Por semana</option>
            <option value="month">Por mes</option>
          </select>
        </div>
      </div>

      {/* KPI Cards */}
      {resumenQ.isLoading
        ? <p className="text-gray-400">Cargando KPIs…</p>
        : resumenQ.data
          ? <KpiCards data={resumenQ.data} />
          : <p className="text-red-500">Error cargando KPIs.</p>
      }

      {/* Ventas por período */}
      <Card title="Ventas por período">
        {ventasQ.isLoading
          ? <p className="text-gray-400 text-sm">Cargando…</p>
          : <VentasLineChart data={ventasQ.data ?? []} />
        }
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top productos */}
        <Card title="Top 10 productos">
          {productosTopQ.isLoading
            ? <p className="text-gray-400 text-sm">Cargando…</p>
            : <ProductosTopBarChart data={productosTopQ.data ?? []} />
          }
        </Card>

        {/* Distribución por estado */}
        <Card title="Distribución por estado">
          {pedidosEstadoQ.isLoading
            ? <p className="text-gray-400 text-sm">Cargando…</p>
            : <PedidosEstadoPieChart data={pedidosEstadoQ.data ?? []} />
          }
        </Card>
      </div>

      {/* Ingresos por forma de pago */}
      <Card title="Ingresos por forma de pago (período seleccionado — pagos aprobados)">
        {ingresosQ.isLoading
          ? <p className="text-gray-400 text-sm">Cargando…</p>
          : <IngresosFormaPagoChart data={ingresosQ.data?.items ?? []} />
        }
      </Card>

      {/* Stock bajo */}
      {resumenQ.data && (
        <Card title="Productos con stock bajo (menos de 5 unidades)">
          {resumenQ.data.productos_stock_bajo.length === 0 ? (
            <p className="text-sm text-gray-400 italic">No hay productos con stock bajo.</p>
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-gray-700">
              {resumenQ.data.productos_stock_bajo.map(p => (
                <li key={p.id} className="flex items-center justify-between py-2">
                  <span className="text-sm text-gray-700 dark:text-gray-200">{p.nombre}</span>
                  <span className="text-sm font-medium text-amber-600 dark:text-amber-400">
                    {p.stock_cantidad} u.
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
    </div>
  )
}
