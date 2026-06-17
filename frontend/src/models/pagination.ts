// src/models/pagination.ts
/**
 * Envoltura de paginación estándar de la API (convención global, sección 5 del spec).
 * Las colecciones paginadas se serializan como:
 *   { items, total, page, size, pages }
 */
export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}
