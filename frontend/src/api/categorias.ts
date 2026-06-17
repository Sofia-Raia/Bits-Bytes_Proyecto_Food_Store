// src/api/categorias.ts
import { http } from './client'
import type { Categoria, CategoriaCreate, CategoriaUpdate, CategoriaList, CategoriaTreeList } from '../models/categoria'

export const getCategoriasApi = (page = 1, size = 100, incluirInactivos = false, nombre?: string) => {
  const params = new URLSearchParams({ page: String(page), size: String(size), incluir_inactivos: String(incluirInactivos) })
  if (nombre) params.set('nombre', nombre)
  return http.get<CategoriaList>(`/categorias/?${params}`).then(r => r.data)
}

export const getCategoriaTreeApi = (incluirInactivos = false) =>
  http.get<CategoriaTreeList>(`/categorias/tree?incluir_inactivos=${incluirInactivos}`).then(r => r.data)

export const getCategoriaApi = (id: number) =>
  http.get<Categoria>(`/categorias/${id}`).then(r => r.data)

export const createCategoriaApi = (data: CategoriaCreate) =>
  http.post<Categoria>('/categorias/', data).then(r => r.data)

export const updateCategoriaApi = (id: number, data: CategoriaUpdate) =>
  http.patch<Categoria>(`/categorias/${id}`, data).then(r => r.data)

export const desactivarCategoriaApi = (id: number) =>
  http.delete(`/categorias/${id}`).then(() => null)

export const reactivarCategoriaApi = (id: number) =>
  http.patch<Categoria>(`/categorias/${id}/reactivar`).then(r => r.data)
