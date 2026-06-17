// src/hooks/useProductos.ts
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Producto, ProductoCreate, ProductoUpdate } from '../models/producto'
import {
  getProductosApi, createProductoApi,
  updateProductoApi, desactivarProductoApi, reactivarProductoApi,
} from '../api/productos'
import { useAuthStore } from '../store/authStore'
import { qk } from '../queries/keys'

const PAGE_SIZE = 10

export type ProductoSortBy = 'nombre' | 'codigo' | 'precio_base' | 'stock_cantidad' | 'created_at'
export type SortDir = 'asc' | 'desc'

/**
 * Controller de productos sobre TanStack Query.
 *
 * Replica la API del antiguo ProductosContext: paginado, orden y búsqueda
 * viven como estado de UI y forman parte del queryKey, de modo que cada
 * combinación se cachea por separado. Las mutaciones invalidan el dominio.
 */
export function useProductos() {
  const qc = useQueryClient()
  const enabled = useAuthStore(s => !!s.user)

  const [page, setPageState] = useState(1)
  const [incluirInactivos, setIncluirInactivos] = useState(false)
  const [categoriaId, setCategoriaId] = useState<number | null>(null)
  const [seleccionado, setSeleccionado] = useState<Producto | null>(null)
  const [busqueda, setBusquedaState] = useState('')
  const [sortBy, setSortBy] = useState<ProductoSortBy>('nombre')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  const params = { page, busqueda, sortBy, sortDir, incluirInactivos, categoriaId }

  const listQuery = useQuery({
    queryKey: qk.productos.list(params),
    queryFn: () => getProductosApi(
      page, PAGE_SIZE, incluirInactivos, busqueda || undefined,
      sortBy, sortDir, categoriaId ?? undefined,
    ),
    enabled,
  })

  const productos: Producto[] = listQuery.data?.items ?? []
  const total = listQuery.data?.total ?? 0
  const loading = listQuery.isFetching
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const recargar = async () => {
    await qc.invalidateQueries({ queryKey: qk.productos.all })
  }

  const setBusqueda = (v: string) => {
    setBusquedaState(v)
    setPageState(1)
  }

  const setPage = (n: number) => {
    setPageState(Math.max(1, Math.min(n, totalPages)))
  }

  const setSort = (by: ProductoSortBy, dir: SortDir) => {
    setSortBy(by)
    setSortDir(dir)
    setPageState(1)
  }

  const toggleInactivos = () => {
    setIncluirInactivos(v => !v)
    setPageState(1)
  }

  const setCategoria = (id: number | null) => {
    setCategoriaId(id)
    setPageState(1)
  }

  const agregarMut = useMutation({
    mutationFn: (data: ProductoCreate) => createProductoApi(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.productos.all }),
  })

  const editarMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProductoUpdate }) => updateProductoApi(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.productos.all })
      setSeleccionado(null)
    },
  })

  const desactivarMut = useMutation({
    mutationFn: (id: number) => desactivarProductoApi(id),
    onSuccess: (_res, id) => {
      if (seleccionado?.id === id) setSeleccionado(null)
      qc.invalidateQueries({ queryKey: qk.productos.all })
    },
  })

  const reactivarMut = useMutation({
    mutationFn: (id: number) => reactivarProductoApi(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.productos.all }),
  })

  const agregar = async (data: ProductoCreate) => { await agregarMut.mutateAsync(data) }
  const editar = async (id: number, data: ProductoUpdate) => { await editarMut.mutateAsync({ id, data }) }
  const desactivar = async (id: number) => { await desactivarMut.mutateAsync(id) }
  const reactivar = async (id: number) => { await reactivarMut.mutateAsync(id) }

  return {
    productos, loading, total,
    page, pageSize: PAGE_SIZE, totalPages, setPage,
    incluirInactivos, seleccionado,
    seleccionar: setSeleccionado, toggleInactivos,
    agregar, editar, desactivar, reactivar, recargar,
    busqueda, setBusqueda,
    sortBy, sortDir, setSort,
    categoriaId, setCategoria,
  }
}
