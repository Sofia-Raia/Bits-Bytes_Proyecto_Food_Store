import type { Paginated } from './pagination'
// src/models/direccion.ts

export interface Direccion {
  id: number
  usuario_id: number
  alias: string | null
  linea1: string
  linea2: string | null
  ciudad: string
  provincia: string | null
  codigo_postal: string | null
  es_principal: boolean
  activo: boolean
  created_at: string
  updated_at: string
}

export interface DireccionCreate {
  alias?: string | null
  linea1: string
  linea2?: string | null
  ciudad: string
  provincia?: string | null
  codigo_postal?: string | null
  es_principal?: boolean
}

export interface DireccionUpdate {
  alias?: string | null
  linea1?: string
  linea2?: string | null
  ciudad?: string
  provincia?: string | null
  codigo_postal?: string | null
  es_principal?: boolean
}

export type DireccionList = Paginated<Direccion>

/** Formatea una dirección para mostrar en una sola línea. */
export function formatDireccion(d: Direccion): string {
  const partes: string[] = [d.linea1]
  if (d.linea2) partes.push(d.linea2)
  partes.push(d.ciudad)
  if (d.provincia) partes.push(d.provincia)
  if (d.codigo_postal) partes.push(`CP ${d.codigo_postal}`)
  return partes.join(', ')
}
