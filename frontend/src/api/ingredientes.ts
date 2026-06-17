// src/api/ingredientes.ts
import { http } from './client'
import type { Ingrediente, IngredienteCreate, IngredienteUpdate, IngredienteList, UnidadMedidaCatalogo } from '../models/ingrediente'

export const getIngredientesApi = (
  page = 1,
  size = 20,
  incluirInactivos = false,
  nombre?: string,
  sortBy = 'nombre',
  sortDir = 'asc',
) => {
  const params = new URLSearchParams({
    page: String(page),
    size: String(size),
    incluir_inactivos: String(incluirInactivos),
    sort_by: sortBy,
    sort_dir: sortDir,
  })
  if (nombre) params.set('nombre', nombre)
  return http.get<IngredienteList>(`/ingredientes/?${params}`).then(r => r.data)
}

/** Catálogo de unidades de medida (solo-lectura). Para poblar selects. */
export const getUnidadesMedidaApi = () =>
  http.get<UnidadMedidaCatalogo[]>('/ingredientes/unidades-medida').then(r => r.data)

export const getIngredienteApi = (id: number) =>
  http.get<Ingrediente>(`/ingredientes/${id}`).then(r => r.data)

export const createIngredienteApi = (data: IngredienteCreate) =>
  http.post<Ingrediente>('/ingredientes/', data).then(r => r.data)

export const updateIngredienteApi = (id: number, data: IngredienteUpdate) =>
  http.patch<Ingrediente>(`/ingredientes/${id}`, data).then(r => r.data)

export const desactivarIngredienteApi = (id: number) =>
  http.delete(`/ingredientes/${id}`).then(() => null)

export const reactivarIngredienteApi = (id: number) =>
  http.patch<Ingrediente>(`/ingredientes/${id}/reactivar`).then(r => r.data)

/** setea el stock al valor absoluto indicado (reposición o ajuste por merma). */
export const actualizarStockIngredienteApi = (id: number, stock_cantidad: number) =>
  http.patch<Ingrediente>(`/ingredientes/${id}/stock`, { stock_cantidad }).then(r => r.data)
