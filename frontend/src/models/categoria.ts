import type { Paginated } from './pagination'
// src/models/categoria.ts
export interface Categoria {
  id: number
  codigo: string
  nombre: string
  descripcion: string | null
  imagen_url: string | null
  parent_id: number | null
  activo: boolean
  created_at: string
  updated_at: string
}

export interface CategoriaTree extends Categoria {
  subcategorias: CategoriaTree[]
}

export interface CategoriaCreate {
  nombre: string
  descripcion?: string | null
  imagen_url?: string | null
  parent_id?: number | null
}

export interface CategoriaUpdate {
  nombre?: string
  descripcion?: string | null
  imagen_url?: string | null
  parent_id?: number | null
}

export type CategoriaList = Paginated<Categoria>

export interface CategoriaTreeList {
  data: CategoriaTree[]
  total: number
}
