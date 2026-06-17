// src/api/pagos.ts
import { http } from './client'
import type { PagoCrearResponse, PagoEstadoResponse } from '../models/pago'

/** Crea la preferencia de MercadoPago para un pedido PENDIENTE propio. */
export const crearPreferenciaApi = (pedido_id: number) =>
  http.post<PagoCrearResponse>('/pagos/create-preference', { pedido_id }).then(r => r.data)

/** Refresca el estado del pago tras volver del checkout de MercadoPago. */
export const confirmarPagoApi = (pedido_id: number, payment_id?: number) =>
  http.post<PagoEstadoResponse>('/pagos/confirm', { pedido_id, payment_id }).then(r => r.data)
