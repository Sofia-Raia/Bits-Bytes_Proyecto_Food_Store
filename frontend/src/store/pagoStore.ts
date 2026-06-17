// src/store/pagoStore.ts
import { create } from 'zustand'
import { crearPreferenciaApi, confirmarPagoApi } from '../api/pagos'
import { ApiError } from '../api/client'
import type { PagoCrearResponse } from '../models/pago'
import { queryClient } from '../lib/queryClient'
import { qk } from '../queries/keys'

interface PagoState {
  loading: boolean
  error: string
  /** Estado del pago tras confirmar: "pendiente" | "aprobado" | "rechazado". */
  estado: string | null
  preferencia: PagoCrearResponse | null
  /** Crea la preferencia y devuelve el init_point para redirigir a MercadoPago. */
  crearPreferencia: (pedidoId: number) => Promise<string | null>
  /** Confirma/refresca el estado del pago y refresca el pedido afectado. */
  confirmarPago: (pedidoId: number, paymentId?: number) => Promise<void>
  /** Limpia el estado transitorio del flujo de pago. */
  reset: () => void
}

export const usePagoStore = create<PagoState>((set) => ({
  loading: false,
  error: '',
  estado: null,
  preferencia: null,

  crearPreferencia: async (pedidoId) => {
    set({ loading: true, error: '' })
    try {
      const resp = await crearPreferenciaApi(pedidoId)
      set({ preferencia: resp })
      if (resp.init_point) {
        return resp.init_point
      }
      set({ loading: false, error: 'No se obtuvo el link de pago de MercadoPago.' })
      return null
    } catch (err) {
      set({
        loading: false,
        error: err instanceof ApiError ? err.message : 'No se pudo iniciar el pago.',
      })
      return null
    }
  },

  confirmarPago: async (pedidoId, paymentId) => {
    set({ loading: true })
    try {
      const resp = await confirmarPagoApi(pedidoId, paymentId)
      set({ estado: resp.estado ?? null, loading: false })
      // El pago pudo cambiar el estado del pedido: refrescamos detalle y listas.
      queryClient.invalidateQueries({ queryKey: qk.pedidos.detail(pedidoId) })
      queryClient.invalidateQueries({ queryKey: qk.pedidos.all })
    } catch {
      set({ estado: null, loading: false })
    }
  },

  reset: () => set({ loading: false, error: '', estado: null, preferencia: null }),
}))
