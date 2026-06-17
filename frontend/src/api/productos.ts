// src/api/productos.ts
import { http } from './client'
import type { Producto, ProductoCreate, ProductoUpdate, ProductoList } from '../models/producto'

export const getProductosApi = (
  page = 1,
  size = 20,
  incluirInactivos = false,
  nombre?: string,
  sortBy = 'nombre',
  sortDir = 'asc',
  categoriaId?: number,
) => {
  const params = new URLSearchParams({
    page: String(page),
    size: String(size),
    incluir_inactivos: String(incluirInactivos),
    sort_by: sortBy,
    sort_dir: sortDir,
  })
  if (nombre) params.set('nombre', nombre)
  if (categoriaId) params.set('categoria_id', String(categoriaId))
  return http.get<ProductoList>(`/productos/?${params}`).then(r => r.data)
}

export const getProductoApi = (id: number) =>
  http.get<Producto>(`/productos/${id}`).then(r => r.data)

export const createProductoApi = (data: ProductoCreate) =>
  http.post<Producto>('/productos/', data).then(r => r.data)

export const updateProductoApi = (id: number, data: ProductoUpdate) =>
  http.patch<Producto>(`/productos/${id}`, data).then(r => r.data)

export const desactivarProductoApi = (id: number) =>
  http.delete(`/productos/${id}`).then(() => null)

export const reactivarProductoApi = (id: number) =>
  http.patch<Producto>(`/productos/${id}/reactivar`).then(r => r.data)

// ── Margen masivo ────────────────────────────────────────────────────────────
export type AplicarMargenScope = 'productos' | 'categoria'

export interface AplicarMargenRequest {
  scope: AplicarMargenScope
  producto_ids?: number[]
  categoria_id?: number
  margen_porcentaje: number
}

export interface AplicarMargenResponse {
  actualizados: { producto_id: number; nombre: string; precio_anterior: number; precio_costo: number; precio_nuevo: number }[]
  ignorados: { producto_id: number; razon: string }[]
}

export const aplicarMargenApi = (data: AplicarMargenRequest) =>
  http.patch<AplicarMargenResponse>('/productos/aplicar-margen', data).then(r => r.data)
