// src/hooks/usePedidos.ts
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type {
  Pedido, PedidoCreate, AvanzarEstadoRequest, EstadoPedido, FormaPago,
} from '../models/pedido'
import {
  getPedidosApi, createPedidoApi, avanzarEstadoApi,
  eliminarPedidoApi, getFormasPagoApi,
} from '../api/pedidos'
import { useAuthStore } from '../store/authStore'
import { qk } from '../queries/keys'

const PAGE_SIZE = 20

/**
 * Alias de compatibilidad: la vista Board (PedidosBoard) importa `PedidoPublic`.
 * Es el mismo shape que el `Pedido` del modelo.
 */
export type PedidoPublic = Pedido

/**
 * Controller de pedidos (staff y cliente) sobre TanStack Query.
 *
 * Conserva la API "rica" que consumen PedidosPage, PedidoForm y
 * AvanzarEstadoModal. A diferencia del antiguo contexto, ya no expone
 * `aplicarActualizacionEnVivo`: la sincronización en vivo por WebSocket se
 * resuelve invalidando `qk.pedidos.all` desde el wsStore, lo que dispara el
 * refetch del listado activo.
 */
export function usePedidos() {
  const qc = useQueryClient()
  const enabled = useAuthStore(s => !!s.user)

  const [page, setPageState] = useState(1)
  const [filtroEstado, setFiltroEstadoState] = useState<EstadoPedido | ''>('')
  const [busqueda, setBusquedaState] = useState('')

  const listQuery = useQuery({
    queryKey: qk.pedidos.list({ page, estado: filtroEstado, busqueda }),
    queryFn: () => getPedidosApi(
      page, PAGE_SIZE,
      filtroEstado || undefined, busqueda || undefined,
    ),
    enabled,
  })

  const formasPagoQuery = useQuery({
    queryKey: qk.pedidos.formasPago,
    queryFn: () => getFormasPagoApi(),
    enabled,
  })

  const pedidos: Pedido[] = listQuery.data?.items ?? []
  const total = listQuery.data?.total ?? 0
  const loading = listQuery.isFetching
  const error = listQuery.error
    ? (listQuery.error instanceof Error ? listQuery.error.message : 'No se pudieron cargar los pedidos.')
    : null
  const formasPago: FormaPago[] = formasPagoQuery.data ?? []
  const pageSize = PAGE_SIZE
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  // Cambiar filtro o búsqueda vuelve a la primera página
  const setFiltroEstado = (e: EstadoPedido | '') => {
    setFiltroEstadoState(e)
    setPageState(1)
  }
  const setBusqueda = (s: string) => {
    setBusquedaState(s)
    setPageState(1)
  }
  const setPage = (n: number) => setPageState(n)

  const recargar = async () => {
    await qc.invalidateQueries({ queryKey: qk.pedidos.all })
  }

  const crearMut = useMutation({
    mutationFn: (data: PedidoCreate) => createPedidoApi(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.pedidos.all }),
  })

  const avanzarMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: AvanzarEstadoRequest }) => avanzarEstadoApi(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.pedidos.all }),
  })

  const eliminarMut = useMutation({
    mutationFn: (id: number) => eliminarPedidoApi(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.pedidos.all }),
  })

  const crear = async (data: PedidoCreate): Promise<Pedido> => crearMut.mutateAsync(data)
  const avanzarEstado = async (id: number, data: AvanzarEstadoRequest): Promise<Pedido> =>
    avanzarMut.mutateAsync({ id, data })
  const eliminar = async (id: number): Promise<void> => { await eliminarMut.mutateAsync(id) }

  return {
    pedidos, loading, error, total,
    page, pageSize, totalPages, setPage,
    filtroEstado, setFiltroEstado,
    busqueda, setBusqueda,
    formasPago, recargar,
    crear, avanzarEstado, eliminar,
  }
}
