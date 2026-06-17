/**
 * src/constants/pedidoEstados.ts
 *
 * Constantes compartidas de estados de pedido.
 * Extraídas de PedidosPage para poder ser reutilizadas en PedidosBoard y otros componentes.
 *
 * INSTRUCCIÓN DE MIGRACIÓN:
 * Si ESTADO_LABELS / ESTADO_COLORES / ESTADO_ICONOS ya existen en PedidosPage.tsx,
 * movalos aquí y reemplazá los originales por imports de este archivo.
 */

/** Etiquetas legibles para cada código de estado del pedido. */
export const ESTADO_LABELS: Record<string, string> = {
  PENDIENTE:  'Pendiente',
  CONFIRMADO: 'Confirmado',
  EN_PREP:    'En preparación',
  ENTREGADO:  'Entregado',
  CANCELADO:  'Cancelado',
};

/**
 * Clases de Tailwind para el badge de cada estado.
 * Usadas por BadgeEstado y por los headers de columna del Board.
 */
export const ESTADO_COLORES: Record<string, string> = {
  PENDIENTE:  'bg-yellow-100  text-yellow-800  border-yellow-300',
  CONFIRMADO: 'bg-blue-100    text-blue-800    border-blue-300',
  EN_PREP:    'bg-purple-100  text-purple-800  border-purple-300',
  ENTREGADO:  'bg-green-100   text-green-800   border-green-300',
  CANCELADO:  'bg-red-100     text-red-800     border-red-300',
};

/** Emoji / ícono para el header de columna del Board. */
export const ESTADO_ICONOS: Record<string, string> = {
  PENDIENTE:  '🕐',
  CONFIRMADO: '✅',
  EN_PREP:    '👨‍🍳',
  ENTREGADO:  '🎉',
  CANCELADO:  '❌',
};

/** Secuencia del flujo principal (columnas del Board, excluye CANCELADO). */
export const ESTADOS_FLUJO: string[] = [
  'PENDIENTE',
  'CONFIRMADO',
  'EN_PREP',
  'ENTREGADO',
];