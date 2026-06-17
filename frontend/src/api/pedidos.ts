// src/api/pedidos.ts
import { http } from './client'
import type {
  Pedido, PedidoList, PedidoCreate, PedidoUpdate,
  AvanzarEstadoRequest, HistorialEntrada, FormaPago,
} from '../models/pedido'

export interface HistorialList {
  data: HistorialEntrada[]
  total: number
}

export const getFormasPagoApi = () =>
  http.get<FormaPago[]>('/pedidos/formas-pago').then(r => r.data)

/** Versión pública del endpoint de formas de pago (codigo/descripcion/habilitado). */
export const getFormasPagoPublicApi = () =>
  http.get<FormaPago[]>('/pedidos/formas-pago').then(r => r.data)

export interface PedidoConfig {
  costo_envio: string
}

/** Parámetros de checkout (costo de envío). Fuente de verdad: backend. */
export const getPedidoConfigApi = () =>
  http.get<PedidoConfig>('/pedidos/config').then(r => r.data)

export const getPedidosApi = (
  page = 1,
  size = 10,
  estado?: string,
  busqueda?: string,
) => {
  const params = new URLSearchParams({
    page: String(page),
    size: String(size),
  })
  if (estado)   params.set('estado', estado)
  if (busqueda) params.set('busqueda', busqueda)
  return http.get<PedidoList>(`/pedidos/?${params}`).then(r => r.data)
}

export const getPedidoApi = (id: number) =>
  http.get<Pedido>(`/pedidos/${id}`).then(r => r.data)

export const createPedidoApi = (data: PedidoCreate) =>
  http.post<Pedido>('/pedidos', data).then(r => r.data)

export const updatePedidoApi = (id: number, data: PedidoUpdate) =>
  http.patch<Pedido>(`/pedidos/${id}`, data).then(r => r.data)

/** Alias semántico para editar pedido PENDIENTE (T4). */
export const editarPedidoApi = updatePedidoApi

export const avanzarEstadoApi = (id: number, data: AvanzarEstadoRequest) =>
  http.patch<Pedido>(`/pedidos/${id}/estado`, data).then(r => r.data)

export const cancelarPedidoApi = (id: number, motivo: string) =>
  avanzarEstadoApi(id, { estado_hacia: 'CANCELADO', motivo })

export const eliminarPedidoApi = (id: number) =>
  http.delete(`/pedidos/${id}`).then(() => null)

export const getHistorialApi = (pedidoId: number) =>
  http.get<HistorialList>(`/pedidos/${pedidoId}/historial`).then(r => r.data)
