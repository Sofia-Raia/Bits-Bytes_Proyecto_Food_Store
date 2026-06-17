// src/api/auth.ts
import axios from 'axios'
import { http, BASE_URL, extraerMensajeError } from './client'
import type { RolCodigo } from '../models/auth'

/**
 * El backend ya no devuelve tokens en el body del login.
 * Solo retorna la información del usuario para hidratar la UI.
 * Los tokens viajan en cookies HttpOnly seteadas por el servidor.
 */
interface LoginResponse {
  id:       number
  email:    string
  nombre:   string
  apellido: string
  roles:    RolCodigo[]
}

/**
 * Extrae el `detail` de un error de axios para mostrar un mensaje útil.
 * Usado por los endpoints de auth que corren con axios "pelado" (sin el
 * interceptor de `http`) para no disparar el refresh/redirect ante un 401
 * de credenciales inválidas.
 */
function mensajeError(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err) && err.response) {
    return extraerMensajeError(err.response.data, fallback)
  }
  return 'Sin conexión con el servidor. Verificá que el backend esté corriendo.'
}

export async function loginApi(email: string, password: string): Promise<LoginResponse> {
  try {
    // axios "pelado" + withCredentials para recibir las cookies HttpOnly del servidor.
    const res = await axios.post<LoginResponse>(
      `${BASE_URL}/auth/login`,
      { email, password },
      { withCredentials: true },
    )
    return res.data
  } catch (err) {
    throw new Error(mensajeError(err, 'Error al iniciar sesión'))
  }
}

export async function logoutApi(): Promise<void> {
  try {
    // El backend borra las cookies HttpOnly. Sin esta llamada, la cookie
    // seguiría activa en el browser hasta su max_age natural.
    await axios.post(`${BASE_URL}/auth/logout`, null, { withCredentials: true })
  } catch {
    // Ignoramos errores de red: el estado local se limpia de todas formas
  }
}

export interface UsuarioPublic {
  id:       number
  email:    string
  nombre:   string
  apellido: string
  celular:  string | null
  roles:    RolCodigo[]
  activo:   boolean
}

export interface UsuarioCreate {
  nombre:   string
  apellido: string
  email:    string
  celular?: string
  password: string
  roles:    RolCodigo[]
}

export interface UsuarioUpdate {
  nombre?:   string
  apellido?: string
  email?:    string
  celular?:  string
  password?: string
  roles?:    RolCodigo[]
}

export interface UsuarioListItem extends UsuarioPublic {
  created_at: string
}

export interface UsuarioListPaginated {
  items: UsuarioListItem[]
  total: number
  page:  number
  size:  number
  pages: number
}

export const getMeApi = () =>
  http.get<UsuarioPublic>('/auth/me').then(r => r.data)

export const listarUsuariosApi = (
  incluir_inactivos = false,
  nombre?: string,
  page = 1,
  size = 20,
  sortBy = 'nombre',
  sortDir = 'asc',
) => {
  const params = new URLSearchParams({
    page:     String(page),
    size:     String(size),
    sort_by:  sortBy,
    sort_dir: sortDir,
  })
  if (incluir_inactivos) params.set('incluir_inactivos', 'true')
  if (nombre)            params.set('nombre', nombre)
  return http.get<UsuarioListPaginated>(`/usuarios/?${params}`).then(r => r.data)
}

export const crearUsuarioApi = (data: UsuarioCreate) =>
  http.post<UsuarioPublic>('/usuarios', data).then(r => r.data)

export const editarUsuarioApi = (id: number, data: UsuarioUpdate) =>
  http.patch<UsuarioPublic>(`/usuarios/${id}`, data).then(r => r.data)

export const desactivarUsuarioApi = (id: number) =>
  http.delete(`/usuarios/${id}`).then(() => undefined)

export const reactivarUsuarioApi = (id: number) =>
  http.patch<UsuarioPublic>(`/usuarios/${id}/reactivar`).then(r => r.data)

// ── FRONTEND-ADAPT-1: Registro público ───────────────────────────────────────

export interface RegisterData {
  nombre: string
  apellido: string
  email: string
  password: string
  celular?: string
}

/**
 * Registra un nuevo usuario con rol CLIENT automático.
 * El backend setea las cookies HttpOnly igual que /login.
 * Usa axios "pelado" (sin el interceptor de `http`) para manejar las cookies
 * correctamente, idéntico al patrón de loginApi.
 */
export async function registerApi(data: RegisterData): Promise<LoginResponse> {
  try {
    const res = await axios.post<LoginResponse>(
      `${BASE_URL}/auth/register`,
      data,
      { withCredentials: true },
    )
    return res.data
  } catch (err) {
    throw new Error(mensajeError(err, 'Error al registrarse'))
  }
}