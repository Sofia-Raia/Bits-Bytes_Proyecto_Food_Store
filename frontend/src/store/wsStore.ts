// src/store/wsStore.ts
import { useEffect } from 'react'
import { create } from 'zustand'
import { queryClient } from '../lib/queryClient'
import { qk } from '../queries/keys'

// ── Tipos ─────────────────────────────────────────────────────────────────────

export interface WsMessage {
  event: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any
}

// ── URL ───────────────────────────────────────────────────────────────────────

/** Deriva la URL del WS de VITE_API_URL: http→ws, https→wss, + "/pedidos/ws". */
function buildWsUrl(): string {
  const apiUrl =
    (import.meta.env.VITE_API_URL as string | undefined) ??
    'http://localhost:8001/api/v1'
  return apiUrl
    .replace(/^http:\/\//, 'ws://')
    .replace(/^https:\/\//, 'wss://') + '/pedidos/ws'
}

const WS_URL = buildWsUrl()

// ── Estado interno no reactivo (socket, timers, refcount, suscripciones) ──────
// Vive a nivel de módulo: el store de Zustand es un singleton, así que una sola
// conexión se comparte entre todos los componentes montados.

let socket: WebSocket | null = null
let retryDelay = 1_000 // ms; se duplica con cada fallo consecutivo (cap 30 s)
let retryTimer: ReturnType<typeof setTimeout> | undefined
let refCount = 0 // cuántos componentes pidieron la conexión (StrictMode-safe)
const ordenesSuscritas = new Set<number>() // rooms order:{id} a re-suscribir al reconectar

// ── Invalidación de queries ante eventos del servidor ─────────────────────────

/**
 * Traduce cada mensaje WS a invalidaciones de TanStack Query.
 * Cualquier evento de pedido invalida todo el dominio "pedidos", lo que refresca
 * listas (tabla/board), "mis pedidos" y el detalle abierto, sin tocar el estado
 * a mano. Es la "invalidación por eventos WS" de la Versión A.
 */
function manejarMensaje(msg: WsMessage): void {
  if (msg.event === 'WS_CONNECTED') {
    queryClient.invalidateQueries({ queryKey: qk.pedidos.all })
    return
  }
  if (msg.event === 'NUEVO_PEDIDO' || msg.event.startsWith('PEDIDO_')) {
    queryClient.invalidateQueries({ queryKey: qk.pedidos.all })
  }
}

// ── Ciclo de vida del socket ──────────────────────────────────────────────────

function abrir(setConnected: (v: boolean) => void): void {
  const ws = new WebSocket(WS_URL)
  socket = ws

  ws.onopen = () => {
    retryDelay = 1_000 // resetear backoff al reconectar con éxito
    setConnected(true)
    // Re-suscribir a los pedidos seguidos antes de la (re)conexión.
    ordenesSuscritas.forEach((id) =>
      ws.send(JSON.stringify({ action: 'subscribe-order', order_id: id })),
    )
    // Evento sintético para resincronizar la data al (re)conectar.
    manejarMensaje({ event: 'WS_CONNECTED', data: null })
  }

  ws.onmessage = (e: MessageEvent) => {
    try {
      manejarMensaje(JSON.parse(e.data as string) as WsMessage)
    } catch {
      // mensaje malformado — ignorar silenciosamente
    }
  }

  ws.onclose = (e: CloseEvent) => {
    setConnected(false)
    if (socket !== ws) return // ya fue reemplazado por una conexión nueva
    socket = null
    // 1000: cierre limpio iniciado por nosotros. 1008: auth rechazada → no reintentar.
    if (e.code === 1000 || e.code === 1008) return
    // Reintento con backoff exponencial mientras siga habiendo interesados.
    if (refCount > 0) {
      retryTimer = setTimeout(() => {
        retryDelay = Math.min(retryDelay * 2, 30_000)
        abrir(setConnected)
      }, retryDelay)
    }
  }

  ws.onerror = () => {
    // onerror siempre va seguido de onclose → la reconexión se maneja allí.
    ws.close()
  }
}

interface WsState {
  connected: boolean
  /** Registra interés en la conexión (refcount); abre el socket si hace falta. */
  connect: () => void
  /** Libera interés; cierra el socket cuando ya nadie lo necesita. */
  disconnect: () => void
  /** Se suscribe al room de un pedido puntual (eventos order:{id}). */
  subscribeToOrder: (orderId: number) => void
  /** Cancela la suscripción al room de un pedido puntual. */
  unsubscribeFromOrder: (orderId: number) => void
}

export const useWsStore = create<WsState>((set) => {
  const setConnected = (v: boolean) => set({ connected: v })

  return {
    connected: false,

    connect: () => {
      refCount += 1
      clearTimeout(retryTimer)
      if (!socket) {
        retryDelay = 1_000
        abrir(setConnected)
      }
    },

    disconnect: () => {
      refCount = Math.max(0, refCount - 1)
      if (refCount === 0) {
        clearTimeout(retryTimer)
        const ws = socket
        socket = null
        ws?.close(1000) // cierre limpio para que el servidor libere el socket
        set({ connected: false })
      }
    },

    subscribeToOrder: (orderId) => {
      ordenesSuscritas.add(orderId)
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ action: 'subscribe-order', order_id: orderId }))
      }
    },

    unsubscribeFromOrder: (orderId) => {
      ordenesSuscritas.delete(orderId)
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ action: 'unsubscribe-order', order_id: orderId }))
      }
    },
  }
})

// ── Hooks de uso en componentes ───────────────────────────────────────────────

/**
 * Abre/cierra la conexión WS durante el ciclo de vida del componente.
 * Idempotente vía refcount, así que es seguro con StrictMode y múltiples montajes.
 */
export function useOrdersRealtime(enabled = true): void {
  useEffect(() => {
    if (!enabled) return
    const { connect, disconnect } = useWsStore.getState()
    connect()
    return () => disconnect()
  }, [enabled])
}

/**
 * Mantiene las suscripciones a rooms order:{id} sincronizadas con la lista de
 * ids activos (p. ej. los pedidos no terminales del cliente).
 */
export function useOrderSubscriptions(orderIds: number[]): void {
  const clave = orderIds.join(',')
  useEffect(() => {
    const { subscribeToOrder, unsubscribeFromOrder } = useWsStore.getState()
    orderIds.forEach(subscribeToOrder)
    return () => orderIds.forEach(unsubscribeFromOrder)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clave])
}
