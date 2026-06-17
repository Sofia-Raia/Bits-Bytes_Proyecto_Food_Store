// src/hooks/useCategorias.ts
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Categoria, CategoriaCreate, CategoriaUpdate, CategoriaTree } from '../models/categoria'
import {
  getCategoriasApi, getCategoriaTreeApi,
  createCategoriaApi, updateCategoriaApi,
  desactivarCategoriaApi, reactivarCategoriaApi,
} from '../api/categorias'
import { useAuthStore } from '../store/authStore'
import { qk } from '../queries/keys'

/**
 * Controller de categorías sobre TanStack Query.
 *
 * Conserva la misma API pública que el antiguo CategoriasContext para que los
 * consumidores sólo cambien el import. Estado de UI (selección, búsqueda,
 * incluirInactivos) vive en useState local; los datos vienen de useQuery y las
 * escrituras de useMutation, que invalidan el dominio completo.
 */
export function useCategorias() {
  const qc = useQueryClient()
  const enabled = useAuthStore(s => !!s.user)

  const [incluirInactivos, setIncluirInactivos] = useState(false)
  const [seleccionado, setSeleccionado] = useState<Categoria | null>(null)
  const [busqueda, setBusquedaState] = useState('')

  const flatQuery = useQuery({
    queryKey: qk.categorias.list(incluirInactivos),
    queryFn: () => getCategoriasApi(1, 100, incluirInactivos),
    enabled,
  })

  const treeQuery = useQuery({
    queryKey: qk.categorias.tree(incluirInactivos),
    queryFn: () => getCategoriaTreeApi(incluirInactivos),
    enabled,
  })

  const categorias: Categoria[] = flatQuery.data?.items ?? []
  const total = flatQuery.data?.total ?? 0
  const tree: CategoriaTree[] = treeQuery.data?.data ?? []
  const loading = flatQuery.isFetching || treeQuery.isFetching

  const recargar = async () => {
    await qc.invalidateQueries({ queryKey: qk.categorias.all })
  }

  const toggleInactivos = () => setIncluirInactivos(v => !v)

  // La búsqueda se conserva como estado de UI; el listado original no la envía
  // al backend, así que se replica ese comportamiento (no-op sobre la query).
  const setBusqueda = (v: string) => setBusquedaState(v)

  const agregarMut = useMutation({
    mutationFn: (data: CategoriaCreate) => createCategoriaApi(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.categorias.all }),
  })

  const editarMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: CategoriaUpdate }) => updateCategoriaApi(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.categorias.all })
      setSeleccionado(null)
    },
  })

  const desactivarMut = useMutation({
    mutationFn: (id: number) => desactivarCategoriaApi(id),
    onSuccess: (_res, id) => {
      qc.invalidateQueries({ queryKey: qk.categorias.all })
      if (seleccionado?.id === id) setSeleccionado(null)
    },
  })

  const reactivarMut = useMutation({
    mutationFn: (id: number) => reactivarCategoriaApi(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.categorias.all }),
  })

  const agregar = async (data: CategoriaCreate) => { await agregarMut.mutateAsync(data) }
  const editar = async (id: number, data: CategoriaUpdate) => { await editarMut.mutateAsync({ id, data }) }
  const desactivar = async (id: number) => { await desactivarMut.mutateAsync(id) }
  const reactivar = async (id: number) => { await reactivarMut.mutateAsync(id) }

  return {
    categorias, tree, loading, total, incluirInactivos, seleccionado,
    seleccionar: setSeleccionado, toggleInactivos,
    agregar, editar, desactivar, reactivar, recargar,
    busqueda, setBusqueda,
  }
}
