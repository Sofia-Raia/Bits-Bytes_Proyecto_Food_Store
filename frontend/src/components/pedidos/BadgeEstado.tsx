/**
 * src/components/pedidos/BadgeEstado.tsx
 *
 * Badge visual para el estado de un pedido.
 * Reutilizado en PedidosPage (tabla) y PedidosBoard (kanban).
 *
 * INSTRUCCIÓN: Si BadgeEstado ya existe en el proyecto, este archivo puede ignorarse.
 * PedidosBoard lo importa desde '../../components/pedidos/BadgeEstado'.
 */
import { ESTADO_COLORES, ESTADO_LABELS } from '../../constants/pedidoEstados';

interface BadgeEstadoProps {
  estado: string;
  /** Tamaño del badge. Default: 'sm'. */
  size?: 'xs' | 'sm' | 'md';
}

export function BadgeEstado({ estado, size = 'sm' }: BadgeEstadoProps) {
  const colores =
    ESTADO_COLORES[estado] ?? 'bg-gray-100 text-gray-700 border-gray-300';

  const sizeClass =
    size === 'xs'
      ? 'text-xs px-1.5 py-0.5'
      : size === 'md'
      ? 'text-sm px-3 py-1'
      : 'text-xs px-2 py-0.5';

  return (
    <span
      className={`inline-flex items-center rounded-full border font-medium
                  ${colores} ${sizeClass}`}
    >
      {ESTADO_LABELS[estado] ?? estado}
    </span>
  );
}
