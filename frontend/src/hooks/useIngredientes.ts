// src/hooks/useIngredientes.ts
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Ingrediente, IngredienteCreate, IngredienteUpdate } from '../models/ingrediente'
import {
  getIngredientesApi, createIngredienteApi,
  updateIngredienteApi, desactivarIngredienteApi, reactivarIngredienteApi,
} from '../api/ingredientes'
import { useAuthStore } from '../store/authStore'
import { qk } from '../queries/keys'

const PAGE_SIZE = 10

export type IngredienteSortBy = 'nombre' | 'codigo' | 'es_alergeno' | 'created_at'
export type SortDir = 'asc' | 'desc'

/**
 * Controller de ingredientes sobre TanStack Query.
 *
 * Misma forma que el antiguo IngredientesContext: paginado, orden y búsqueda
 * como estado de UI que entra en el queryKey. Las mutaciones invalidan el
 * dominio completo para refrescar el listado activo.
 */
export function useIngredientes() {
  const qc = useQueryClient()
  const enabled = useAuthStore(s => !!s.user)

  const [page, setPageState] = useState(1)
  const [incluirInactivos, setIncluirInactivos] = useState(false)
  const [seleccionado, setSeleccionado] = useState<Ingrediente | null>(null)
  const [busqueda, setBusquedaState] = useState('')
  const [sortBy, setSortBy] = useState<IngredienteSortBy>('nombre')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  const params = { page, busqueda, sortBy, sortDir, incluirInactivos }

  const listQuery = useQuery({
    queryKey: qk.ingredientes.list(params),
    queryFn: () => getIngredientesApi(
      page, PAGE_SIZE, incluirInactivos, busqueda || undefined,
      sortBy, sortDir,
    ),
    enabled,
  })

  const ingredientes: Ingrediente[] = listQuery.data?.items ?? []
  const total = listQuery.data?.total ?? 0
  const loading = listQuery.isFetching
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const recargar = async () => {
    await qc.invalidateQueries({ queryKey: qk.ingredientes.all })
  }

  const setBusqueda = (v: string) => {
    setBusquedaState(v)
    setPageState(1)
  }

  const setPage = (n: number) => {
    setPageState(Math.max(1, Math.min(n, totalPages)))
  }

  const setSort = (by: IngredienteSortBy, dir: SortDir) => {
    setSortBy(by)
    setSortDir(dir)
    setPageState(1)
  }

  const toggleInactivos = () => {
    setIncluirInactivos(v => !v)
    setPageState(1)
  }

  const agregarMut = useMutation({
    mutationFn: (data: IngredienteCreate) => createIngredienteApi(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.ingredientes.all }),
  })

  const editarMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: IngredienteUpdate }) => updateIngredienteApi(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.ingredientes.all })
      setSeleccionado(null)
    },
  })

  const desactivarMut = useMutation({
    mutationFn: (id: number) => desactivarIngredienteApi(id),
    onSuccess: (_res, id) => {
      if (seleccionado?.id === id) setSeleccionado(null)
      qc.invalidateQueries({ queryKey: qk.ingredientes.all })
    },
  })

  const reactivarMut = useMutation({
    mutationFn: (id: number) => reactivarIngredienteApi(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.ingredientes.all }),
  })

  const agregar = async (data: IngredienteCreate) => { await agregarMut.mutateAsync(data) }
  const editar = async (id: number, data: IngredienteUpdate) => { await editarMut.mutateAsync({ id, data }) }
  const desactivar = async (id: number) => { await desactivarMut.mutateAsync(id) }
  const reactivar = async (id: number) => { await reactivarMut.mutateAsync(id) }

  return {
    ingredientes, loading, total,
    page, pageSize: PAGE_SIZE, totalPages, setPage,
    incluirInactivos, seleccionado,
    seleccionar: setSeleccionado, toggleInactivos,
    agregar, editar, desactivar, reactivar, recargar,
    busqueda, setBusqueda,
    sortBy, sortDir, setSort,
  }
}
