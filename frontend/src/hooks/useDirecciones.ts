// src/hooks/useDirecciones.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Direccion, DireccionCreate, DireccionUpdate } from '../models/direccion'
import {
  getDireccionesApi, createDireccionApi,
  updateDireccionApi, deleteDireccionApi, marcarPrincipalApi,
} from '../api/direcciones'
import { useAuthStore } from '../store/authStore'
import { qk } from '../queries/keys'

/**
 * Controller de direcciones del usuario autenticado sobre TanStack Query.
 *
 * Mantiene la API del antiguo DireccionesContext. Todas las mutaciones
 * invalidan el dominio de direcciones; las que pueden alterar la dirección
 * principal del resto del listado se cubren con la misma invalidación global.
 */
export function useDirecciones() {
  const qc = useQueryClient()
  const enabled = useAuthStore(s => !!s.user)

  const listQuery = useQuery({
    queryKey: qk.direcciones.list(),
    queryFn: () => getDireccionesApi(),
    enabled,
  })

  const direcciones: Direccion[] = listQuery.data?.items ?? []
  const loading = listQuery.isFetching

  const recargar = async () => {
    await qc.invalidateQueries({ queryKey: qk.direcciones.all })
  }

  const agregarMut = useMutation({
    mutationFn: (data: DireccionCreate) => createDireccionApi(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.direcciones.all }),
  })

  const editarMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: DireccionUpdate }) => updateDireccionApi(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.direcciones.all }),
  })

  const eliminarMut = useMutation({
    mutationFn: (id: number) => deleteDireccionApi(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.direcciones.all }),
  })

  const marcarPrincipalMut = useMutation({
    mutationFn: (id: number) => marcarPrincipalApi(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.direcciones.all }),
  })

  const agregar = async (data: DireccionCreate) => { await agregarMut.mutateAsync(data) }
  const editar = async (id: number, data: DireccionUpdate) => { await editarMut.mutateAsync({ id, data }) }
  const eliminar = async (id: number) => { await eliminarMut.mutateAsync(id) }
  const marcarPrincipal = async (id: number) => { await marcarPrincipalMut.mutateAsync(id) }

  return { direcciones, loading, agregar, editar, eliminar, marcarPrincipal, recargar }
}
