// src/models/estadistica.ts
export interface ProductoStockBajo {
  id: number
  nombre: string
  stock_cantidad: number
}

export interface ResumenResponse {
  ventas_hoy: number
  ventas_mes: number
  ticket_promedio: number
  pedidos_activos: number
  productos_stock_bajo: ProductoStockBajo[]
}

export interface VentasPeriodoItem {
  periodo: string
  total_ventas: number
  cantidad_pedidos: number
}

export interface ProductoTopItem {
  producto_id: number
  nombre: string
  ingresos: number
  cantidad_vendida: number
}

export interface PedidosEstadoItem {
  estado_codigo: string
  cantidad: number
}

export interface IngresosItem {
  forma_pago_codigo: string
  total: number
  cantidad: number
}

export interface IngresosResponse {
  items: IngresosItem[]
}
