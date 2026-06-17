// src/api/direcciones.ts
import { http } from './client'
import type { Direccion, DireccionCreate, DireccionUpdate, DireccionList } from '../models/direccion'

export const getDireccionesApi = (usuarioId?: number) => {
  const params = new URLSearchParams({ page: '1', size: '100' })
  if (usuarioId) params.set('usuario_id', String(usuarioId))
  return http.get<DireccionList>(`/direcciones/?${params}`).then(r => r.data)
}

export const getDireccionApi = (id: number) =>
  http.get<Direccion>(`/direcciones/${id}`).then(r => r.data)

export const createDireccionApi = (data: DireccionCreate) =>
  http.post<Direccion>('/direcciones/', data).then(r => r.data)

export const updateDireccionApi = (id: number, data: DireccionUpdate) =>
  http.patch<Direccion>(`/direcciones/${id}`, data).then(r => r.data)

export const deleteDireccionApi = (id: number) =>
  http.delete(`/direcciones/${id}`).then(() => null)

export const marcarPrincipalApi = (id: number) =>
  http.patch<Direccion>(`/direcciones/${id}/principal`).then(r => r.data)
