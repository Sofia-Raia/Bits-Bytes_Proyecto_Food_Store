import type { Paginated } from './pagination'
// src/models/ingrediente.ts

/** Una unidad de medida del catálogo. GET /ingredientes/unidades-medida. */
export interface UnidadMedidaCatalogo {
  id: number
  codigo: string
  nombre: string
  simbolo: string
  tipo: string
}

export interface Ingrediente {
  id: number
  codigo: string
  nombre: string
  descripcion: string | null
  es_alergeno: boolean
  costo: number
  /** Código de la unidad de medida (KG, G, L, ML, UNIDADES, DOC, M2, ...). */
  unidad_medida: string
  unidad_medida_id: number
  unidad_simbolo: string | null
  /** Stock disponible. NUMERIC(10,3) del backend → float en JSON. */
  stock_cantidad: number
  activo: boolean
  created_at: string
  updated_at: string
}

export interface IngredienteCreate {
  nombre: string
  descripcion?: string | null
  es_alergeno: boolean
  costo: number
  /** Código de la unidad (el backend lo resuelve al id del catálogo). */
  unidad_medida: string
  stock_cantidad: number
}

export interface IngredienteUpdate {
  nombre?: string
  descripcion?: string | null
  es_alergeno?: boolean
  costo?: number
  unidad_medida?: string
  stock_cantidad?: number
}

export type IngredienteList = Paginated<Ingrediente>