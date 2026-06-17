import type { Paginated } from './pagination'
// src/models/pedido.ts
import type { RolCodigo } from './auth'

export type EstadoPedido =
  | 'PENDIENTE'
  | 'CONFIRMADO'
  | 'EN_PREP'
  | 'ENTREGADO'
  | 'CANCELADO'

export interface FormaPago {
  codigo: string
  descripcion: string
  habilitado: boolean
}

export interface DetallePedido {
  pedido_id: number
  producto_id: number
  nombre_snapshot: string
  precio_snapshot: number
  cantidad: number
  subtotal_snap: number
  personalizacion: number[] | null
}

export interface Pedido {
  id: number
  codigo: string
  usuario_id: number
  usuario_nombre?: string | null
  estado_codigo: EstadoPedido
  forma_pago_codigo: string
  direccion_id: number | null
  direccion_snapshot: string | null
  notas: string | null
  subtotal: number
  descuento: number
  costo_envio: number
  total: number
  created_at: string
  updated_at: string
  detalles: DetallePedido[]
  historial: HistorialEntrada[]
}

export type PedidoList = Paginated<Pedido>

export interface ItemPedidoRequest {
  producto_id: number
  cantidad: number
  personalizacion?: number[] | null
}

export interface PedidoCreate {
  forma_pago_codigo: string
  direccion_id?: number | null
  notas?: string | null
  items: ItemPedidoRequest[]
  usuario_id?: number | null
}

export interface PedidoUpdate {
  forma_pago_codigo?: string | null
  notas?: string | null
  direccion_id?: number | null
  items?: ItemPedidoRequest[] | null
}

export interface AvanzarEstadoRequest {
  estado_hacia: EstadoPedido
  motivo?: string | null
}

export interface HistorialEntrada {
  id: number
  pedido_id: number
  estado_desde: EstadoPedido | null
  estado_hacia: EstadoPedido
  usuario_id: number | null
  motivo: string | null
  created_at: string
}

// ── Matriz de transiciones válidas (§E.7.1) ──────────────────────────────────
type RolPermitido = 'ADMIN' | 'PEDIDOS' | 'CLIENT_OWNER'

interface TransicionDef {
  hacia: EstadoPedido
  roles: RolPermitido[]
}

const TRANSICIONES_VALIDAS: Record<string, TransicionDef[]> = {
  PENDIENTE: [
    { hacia: 'CONFIRMADO', roles: ['PEDIDOS', 'ADMIN'] },
    { hacia: 'CANCELADO',  roles: ['CLIENT_OWNER', 'PEDIDOS', 'ADMIN'] },
  ],
  CONFIRMADO: [
    { hacia: 'EN_PREP',   roles: ['PEDIDOS', 'ADMIN'] },
    { hacia: 'CANCELADO', roles: ['CLIENT_OWNER', 'PEDIDOS', 'ADMIN'] },  // BACKEND-4
  ],
  EN_PREP: [
    { hacia: 'ENTREGADO', roles: ['PEDIDOS', 'ADMIN'] },
    { hacia: 'CANCELADO', roles: ['ADMIN'] },
  ],
}

/** Devuelve los estados a los que puede avanzar este pedido dado el rol del usuario. */
export function getTransicionesValidas(
  estado: EstadoPedido,
  roles: RolCodigo[],
  esOwner: boolean,
): EstadoPedido[] {
  const opciones = TRANSICIONES_VALIDAS[estado] ?? []
  return opciones
    .filter(t =>
      t.roles.some(r => {
        if (r === 'CLIENT_OWNER') return esOwner
        return roles.includes(r as RolCodigo)
      }),
    )
    .map(t => t.hacia)
}

// ── Helpers de presentación ───────────────────────────────────────────────────
export const ESTADO_LABELS: Record<EstadoPedido, string> = {
  PENDIENTE:  'Pendiente',
  CONFIRMADO: 'Confirmado',
  EN_PREP:    'En preparación',
  ENTREGADO:  'Entregado',
  CANCELADO:  'Cancelado',
}

export const ESTADO_COLORES: Record<EstadoPedido, string> = {
  PENDIENTE:  'bg-yellow-100 text-yellow-800 border-yellow-200',
  CONFIRMADO: 'bg-blue-100 text-blue-800 border-blue-200',
  EN_PREP:    'bg-orange-100 text-orange-800 border-orange-200',
  ENTREGADO:  'bg-green-100 text-green-800 border-green-200',
  CANCELADO:  'bg-red-100 text-red-800 border-red-200',
}

export const ESTADO_ICONOS: Record<EstadoPedido, string> = {
  PENDIENTE:  '⏳',
  CONFIRMADO: '✅',
  EN_PREP:    '👨‍🍳',
  ENTREGADO:  '📦',
  CANCELADO:  '❌',
}

export const ESTADOS_TERMINALES: EstadoPedido[] = ['ENTREGADO', 'CANCELADO']