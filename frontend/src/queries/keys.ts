// src/queries/keys.ts

/**
 * Parámetros de listado de productos / ingredientes (paginado + orden + filtro).
 * Forman parte del queryKey para que TanStack Query cachee por combinación.
 */
export interface ListaParams {
  page: number
  busqueda: string
  sortBy: string
  sortDir: string
  incluirInactivos: boolean
}

/**
 * Fábrica central de queryKeys descriptivos.
 *
 * Cada dominio expone:
 * - `all`: prefijo raíz, usado para invalidar todo el dominio de una sola vez.
 * - keys específicas que incluyen los parámetros relevantes (paginado, filtros, id).
 *
 * Mantener las keys jerárquicas (`[dominio, tipo, params]`) permite invalidar
 * por prefijo: invalidar `['pedidos']` alcanza listas, "mis pedidos" y detalles.
 */
export const qk = {
  categorias: {
    all: ['categorias'] as const,
    list: (incluirInactivos: boolean) =>
      ['categorias', 'list', { incluirInactivos }] as const,
    tree: (incluirInactivos: boolean) =>
      ['categorias', 'tree', { incluirInactivos }] as const,
  },

  productos: {
    all: ['productos'] as const,
    list: (params: ListaParams) => ['productos', 'list', params] as const,
    publico: (page: number, busqueda: string, categoriaId: number | null = null) =>
      ['productos', 'publico', { page, busqueda, categoriaId }] as const,
    detail: (id: number) => ['productos', 'detail', id] as const,
  },

  ingredientes: {
    all: ['ingredientes'] as const,
    list: (params: ListaParams) => ['ingredientes', 'list', params] as const,
  },

  direcciones: {
    all: ['direcciones'] as const,
    list: (usuarioId?: number | null) =>
      ['direcciones', 'list', { usuarioId: usuarioId ?? null }] as const,
  },

  pedidos: {
    all: ['pedidos'] as const,
    list: (params: { page: number; estado: string; busqueda: string }) =>
      ['pedidos', 'list', params] as const,
    mis: (page: number) => ['pedidos', 'mis', { page }] as const,
    detail: (id: number) => ['pedidos', 'detail', id] as const,
    formasPago: ['pedidos', 'formas-pago'] as const,
    config: ['pedidos', 'config'] as const,
  },

  usuarios: {
    all: ['usuarios'] as const,
    list: (params: {
      page: number
      busqueda: string
      sortBy: string
      sortDir: string
      incluirInactivos: boolean
    }) => ['usuarios', 'list', params] as const,
  },

  estadisticas: {
    resumen: ['estadisticas', 'resumen'] as const,
    ventas: (desde?: string, hasta?: string, agrupacion?: string) =>
      ['estadisticas', 'ventas', { desde, hasta, agrupacion }] as const,
    productosTop: (limit: number) => ['estadisticas', 'productos-top', limit] as const,
    pedidosPorEstado: ['estadisticas', 'pedidos-por-estado'] as const,
    ingresos: (desde?: string, hasta?: string) =>
      ['estadisticas', 'ingresos', { desde, hasta }] as const,
  },
} as const
