// src/api/estadisticas.ts
import { http } from './client'
import type {
  ResumenResponse, VentasPeriodoItem, ProductoTopItem,
  PedidosEstadoItem, IngresosResponse,
} from '../models/estadistica'

export const getResumenApi = () =>
  http.get<ResumenResponse>('/estadisticas/resumen').then(r => r.data)

export const getVentasApi = (desde?: string, hasta?: string, agrupacion = 'day') =>
  http.get<VentasPeriodoItem[]>('/estadisticas/ventas', {
    params: { desde, hasta, agrupacion },
  }).then(r => r.data)

export const getProductosTopApi = (limit = 10) =>
  http.get<ProductoTopItem[]>('/estadisticas/productos-top', { params: { limit } }).then(r => r.data)

export const getPedidosPorEstadoApi = () =>
  http.get<PedidosEstadoItem[]>('/estadisticas/pedidos-por-estado').then(r => r.data)

export const getIngresosApi = (desde?: string, hasta?: string) =>
  http.get<IngresosResponse>('/estadisticas/ingresos', {
    params: { desde, hasta },
  }).then(r => r.data)
