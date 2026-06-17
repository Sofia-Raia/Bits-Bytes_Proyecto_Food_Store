import type { Paginated } from './pagination'
// src/models/producto.ts
export type TipoProducto = 'TERMINADO' | 'MANUFACTURADO'
export type UnidadMedida = 'KG' | 'L' | 'UNIDADES'

export interface CategoriaEnProducto {
  id: number
  nombre: string
  es_principal: boolean
}

export interface IngredienteEnProducto {
  id: number
  nombre: string
  es_alergeno: boolean
  es_removible: boolean
  es_opcional: boolean
  cantidad: number
  unidad_medida: UnidadMedida
  costo_unitario: number
  subtotal_costo: number
}

export interface ProductoIngredienteInput {
  ingrediente_id: number
  /** Cantidad necesaria del ingrediente por 1 unidad del producto. */
  cantidad: number
  es_removible: boolean
  es_opcional: boolean
}

export interface Producto {
  id: number
  codigo: string
  nombre: string
  descripcion: string | null
  precio_base: number
  /** Calculado on-the-fly en el backend. 0 si tipo=TERMINADO. */
  precio_costo: number
  /** Galería de imágenes. Primer elemento = imagen principal. */
  imagenes_url: string[]
  /** Tiempo estimado de preparación en minutos. */
  tiempo_prep_min: number | null
  stock_cantidad: number
  disponible: boolean
  /** ERD: unidad de venta (FK al catálogo UnidadMedida). null = se vende por pieza. */
  unidad_venta_id?: number | null
  activo: boolean
  tipo: TipoProducto
  categorias: CategoriaEnProducto[]
  ingredientes: IngredienteEnProducto[]
  created_at: string
  updated_at: string
}

export interface ProductoCreate {
  nombre: string
  descripcion?: string | null
  precio_base: number
  imagenes_url: string[]
  tiempo_prep_min?: number | null
  stock_cantidad: number
  disponible: boolean
  tipo: TipoProducto
  categoria_ids: number[]
  ingredientes: ProductoIngredienteInput[]
}

export interface ProductoUpdate {
  nombre?: string
  descripcion?: string | null
  precio_base?: number
  imagenes_url?: string[]
  tiempo_prep_min?: number | null
  stock_cantidad?: number
  disponible?: boolean
  tipo?: TipoProducto
  categoria_ids?: number[]
  ingredientes?: ProductoIngredienteInput[]
}

export type ProductoList = Paginated<Producto>
