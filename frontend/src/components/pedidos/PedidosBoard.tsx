/**
 * src/components/pedidos/PedidosBoard.tsx
 *
 * Vista kanban de pedidos agrupados por estado.
 *
 * Columnas del flujo principal: PENDIENTE → CONFIRMADO → EN_PREP → ENTREGADO
 * Sección separada abajo: CANCELADO
 *
 * Reutiliza ESTADO_LABELS / ESTADO_COLORES / ESTADO_ICONOS / ESTADOS_FLUJO desde constants.
 * Reutiliza BadgeEstado para el badge de estado dentro de cada tarjeta.
 * Reutiliza AvanzarEstadoModal: el board sube el pedido seleccionado vía onAvanzar()
 * al padre (PedidosPage), que gestiona un único modal compartido entre tabla y board.
 */
import { type PedidoPublic } from '../../hooks/usePedidos';
import { BadgeEstado } from './BadgeEstado';
import {
  ESTADO_COLORES,
  ESTADO_ICONOS,
  ESTADO_LABELS,
  ESTADOS_FLUJO,
} from '../../constants/pedidoEstados';

// ── Tipos ─────────────────────────────────────────────────────────────────────

interface PedidosBoardProps {
  /** Lista de pedidos (derivada del contexto por PedidosPage). */
  pedidos: PedidoPublic[];
  /**
   * Callback para abrir el modal de avanzar estado.
   * PedidosPage gestiona el modal; el board solo indica cuál pedido avanzar.
   */
  onAvanzar: (pedido: PedidoPublic) => void;
  /** Conjunto de roles del usuario actual (para mostrar / ocultar botón Avanzar). */
  roles: string[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Formatea fecha ISO a hora local legible (HH:MM). */
function formatHora(isoStr: string): string {
  try {
    return new Date(isoStr).toLocaleTimeString('es-AR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoStr;
  }
}

/** Formatea fecha ISO a fecha + hora legible. */
function formatFecha(isoStr: string): string {
  try {
    return new Date(isoStr).toLocaleDateString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoStr;
  }
}

/** Formatea monto en pesos argentinos. */
function formatMonto(n: number): string {
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 2,
  }).format(n);
}

/** El staff (ADMIN o PEDIDOS) puede avanzar estados; CLIENT no. */
function puedeAvanzar(roles: string[]): boolean {
  return roles.some((r) => r === 'ADMIN' || r === 'PEDIDOS');
}

// ── Tarjeta de pedido ─────────────────────────────────────────────────────────

interface TarjetaProps {
  pedido: PedidoPublic;
  onAvanzar: (pedido: PedidoPublic) => void;
  mostrarBotonAvanzar: boolean;
}

function TarjetaPedido({ pedido, onAvanzar, mostrarBotonAvanzar }: TarjetaProps) {
  const esTerminal =
    pedido.estado_codigo === 'ENTREGADO' || pedido.estado_codigo === 'CANCELADO';

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-3 flex flex-col gap-2 hover:shadow-md transition-shadow">
      {/* Código + badge */}
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs font-semibold text-gray-700 truncate">
          {pedido.codigo}
        </span>
        <BadgeEstado estado={pedido.estado_codigo} />
      </div>

      {/* Cliente */}
      <p className="text-sm text-gray-600 truncate">
        Cliente <span className="font-medium text-gray-800">#{pedido.usuario_id}{pedido.usuario_nombre ? ` · ${pedido.usuario_nombre}` : ''}</span>
      </p>

      {/* Hora de creación */}
      <p className="text-xs text-gray-400">
        {formatFecha(pedido.created_at)}
      </p>

      {/* Total */}
      <p className="text-sm font-semibold text-gray-900">
        {formatMonto(pedido.total)}
      </p>

      {/* Notas (si hay) */}
      {pedido.notas && (
        <p className="text-xs text-gray-500 italic truncate" title={pedido.notas}>
          {pedido.notas}
        </p>
      )}

      {/* Botón Avanzar */}
      {mostrarBotonAvanzar && !esTerminal && (
        <button
          onClick={() => onAvanzar(pedido)}
          className="mt-1 w-full text-xs font-medium px-2 py-1.5 rounded
                     bg-indigo-50 text-indigo-700 border border-indigo-200
                     hover:bg-indigo-100 hover:border-indigo-400 transition-colors"
        >
          Avanzar →
        </button>
      )}
    </div>
  );
}

// ── Header de columna ─────────────────────────────────────────────────────────

interface ColumnaHeaderProps {
  estado: string;
  count: number;
}

function ColumnaHeader({ estado, count }: ColumnaHeaderProps) {
  const colorBase = ESTADO_COLORES[estado] ?? 'bg-gray-100 text-gray-700 border-gray-300';
  return (
    <div
      className={`flex items-center justify-between px-3 py-2 rounded-t-lg border-b-2
                  font-semibold text-sm ${colorBase}`}
    >
      <span>
        <span className="mr-1">{ESTADO_ICONOS[estado]}</span>
        {ESTADO_LABELS[estado] ?? estado}
      </span>
      <span
        className="ml-2 inline-flex items-center justify-center
                   min-w-[1.5rem] h-6 rounded-full bg-white/60 text-xs font-bold px-1.5"
      >
        {count}
      </span>
    </div>
  );
}

// ── Columna ───────────────────────────────────────────────────────────────────

interface ColumnaProps {
  estado: string;
  pedidos: PedidoPublic[];
  onAvanzar: (pedido: PedidoPublic) => void;
  mostrarBotonAvanzar: boolean;
}

function Columna({ estado, pedidos, onAvanzar, mostrarBotonAvanzar }: ColumnaProps) {
  return (
    <div className="flex flex-col min-w-[220px] max-w-[260px] flex-shrink-0">
      <ColumnaHeader estado={estado} count={pedidos.length} />
      <div
        className="flex-1 overflow-y-auto p-2 flex flex-col gap-2
                   bg-gray-50 rounded-b-lg border border-t-0 border-gray-200
                   min-h-[200px] max-h-[calc(100vh-260px)]"
      >
        {pedidos.length === 0 ? (
          <p className="text-xs text-gray-400 text-center mt-4">Sin pedidos</p>
        ) : (
          pedidos.map((p) => (
            <TarjetaPedido
              key={p.id}
              pedido={p}
              onAvanzar={onAvanzar}
              mostrarBotonAvanzar={mostrarBotonAvanzar}
            />
          ))
        )}
      </div>
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────

export function PedidosBoard({ pedidos, onAvanzar, roles }: PedidosBoardProps) {
  const puedeMover = puedeAvanzar(roles);

  // Agrupar pedidos por estado
  const porEstado = (estado: string) =>
    pedidos.filter((p) => p.estado_codigo === estado);

  const cancelados = porEstado('CANCELADO');

  return (
    <div className="flex flex-col gap-4">
      {/* ── Flujo principal: scroll horizontal ── */}
      <div className="flex gap-3 overflow-x-auto pb-2">
        {ESTADOS_FLUJO.map((estado) => (
          <Columna
            key={estado}
            estado={estado}
            pedidos={porEstado(estado)}
            onAvanzar={onAvanzar}
            mostrarBotonAvanzar={puedeMover}
          />
        ))}
      </div>

      {/* ── Sección CANCELADO (separada abajo) ── */}
      {cancelados.length > 0 && (
        <details className="group">
          <summary
            className="cursor-pointer select-none flex items-center gap-2
                       text-sm font-medium text-red-700 hover:text-red-900
                       list-none"
          >
            <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
            <span>{ESTADO_ICONOS.CANCELADO} Cancelados ({cancelados.length})</span>
          </summary>
          <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2">
            {cancelados.map((p) => (
              <TarjetaPedido
                key={p.id}
                pedido={p}
                onAvanzar={onAvanzar}
                mostrarBotonAvanzar={false} /* cancelado = terminal */
              />
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
