// src/models/pago.ts
// Tipos del módulo de pagos (MercadoPago — Parte 4)

/** Respuesta de POST /pagos/create-preference */
export interface PagoCrearResponse {
  pago_id: number
  preference_id: string
  init_point?: string | null
  public_key?: string | null
}

/** Respuesta de POST /pagos/confirm */
export interface PagoEstadoResponse {
  estado?: string | null   // "pendiente" | "aprobado" | "rechazado"
  pedido_id: number
}

/** Resultado del redirect de MercadoPago (segmento de la URL) */
export type PagoResultadoStatus = 'success' | 'failure' | 'pending'
