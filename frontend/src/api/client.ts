// src/api/client.ts
import axios, {
  AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios'

export const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

// Clave de localStorage donde authStore guarda los datos de UI del usuario
// (email, nombre, apellido, roles). NO contiene tokens — esos viven en cookies
// HttpOnly que el browser maneja de forma transparente e inaccesible desde JS.
const STORAGE_KEY = 'auth_user'

/**
 * Devuelve true si hay datos de sesión de UI en localStorage.
 * No garantiza que la cookie de acceso sea válida — eso lo determina el backend.
 * Usar solo como guardia de "¿tiene sentido intentar un fetch ahora?".
 */
export function isAuthenticated(): boolean {
  return !!localStorage.getItem(STORAGE_KEY)
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export class NetworkError extends Error {
  constructor(
    message = 'Sin conexión con el servidor. Verificá que el backend esté corriendo.',
  ) {
    super(message)
    this.name = 'NetworkError'
  }
}

/** Forma de los cuerpos de error que devuelve el backend. */
type BackendError = {
  error?: { message?: string; code?: string }
  detail?: string | Array<{ msg?: string }>
}

/**
 * Extrae el mensaje legible de un cuerpo de error del backend.
 * Prioriza el envelope propio { error: { code, message } }; si no, cae a los
 * formatos de FastAPI (`detail` string, o array de validación 422); por último,
 * usa el fallback provisto.
 */
export function extraerMensajeError(data: unknown, fallback: string): string {
  const d = data as BackendError | undefined
  if (d?.error?.message) return d.error.message
  if (typeof d?.detail === 'string') return d.detail
  if (Array.isArray(d?.detail) && d.detail[0]?.msg) return String(d.detail[0].msg)
  return fallback
}

/**
 * Instancia de Axios para todas las llamadas autenticadas.
 * withCredentials adjunta las cookies HttpOnly en cada request, igual que el
 * antiguo `credentials: 'include'` de fetch.
 */
export const http: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

/**
 * Intenta refrescar la sesión enviando la cookie refresh_token al backend.
 * Usa axios "pelado" (no la instancia `http`) para no disparar el interceptor
 * de respuesta y evitar un bucle de refresh.
 */
async function tryRefresh(): Promise<boolean> {
  try {
    const res = await axios.post(`${BASE_URL}/auth/refresh`, null, {
      withCredentials: true,
    })
    return res.status >= 200 && res.status < 300
  } catch {
    return false
  }
}

// Deduplica refresh concurrentes: si varias requests fallan con 401 a la vez,
// comparten una única promesa de refresh en lugar de pegarle N veces al backend.
let refreshPromise: Promise<boolean> | null = null

/**
 * Interceptor de respuesta:
 * - Sin response (error de red / timeout) → NetworkError.
 * - 401 (una sola vez por request): intenta refrescar y reintenta; si falla,
 *   limpia la sesión de UI y redirige a /login.
 * - Resto de errores: normaliza a ApiError(status, detail) para que los
 *   componentes sigan usando `e instanceof ApiError ? e.message : ...`.
 */
http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<BackendError>) => {
    const original = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined

    if (!error.response) {
      if (error.code === 'ECONNABORTED') {
        throw new NetworkError('La solicitud tardó demasiado. Verificá tu conexión.')
      }
      throw new NetworkError()
    }

    const status = error.response.status

    if (status === 401 && original && !original._retry) {
      original._retry = true
      refreshPromise = refreshPromise ?? tryRefresh()
      const refreshed = await refreshPromise
      refreshPromise = null
      if (refreshed) {
        return http(original)
      }
      localStorage.removeItem(STORAGE_KEY)
      window.location.replace('/login')
      throw new ApiError(401, 'Sesión expirada')
    }

    throw new ApiError(status, extraerMensajeError(error.response.data, 'Error en la solicitud'))
  },
)