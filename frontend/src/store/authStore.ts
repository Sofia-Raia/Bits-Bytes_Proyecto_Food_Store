// src/store/authStore.ts
import { create } from 'zustand'
import type { AuthUser, RolCodigo } from '../models/auth'
import { loginApi, logoutApi, registerApi, type RegisterData } from '../api/auth'
import { queryClient } from '../lib/queryClient'

/**
 * Solo guardamos información de UI en localStorage (nombre, email, roles).
 * Los tokens viven en cookies HttpOnly — el browser los maneja de forma
 * transparente y nunca son accesibles desde JavaScript.
 */
const STORAGE_KEY = 'auth_user'

/** Lee el usuario persistido para hidratar el estado inicial del store. */
function loadUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as AuthUser) : null
  } catch {
    return null
  }
}

interface AuthState {
  user: AuthUser | null
  login: (email: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: loadUser(),

  /** Inicia sesión, persiste los datos de UI e hidrata las queries privadas. */
  login: async (email, password) => {
    const data = await loginApi(email, password)
    const user: AuthUser = {
      id:       data.id,
      email:    data.email,
      nombre:   data.nombre,
      apellido: data.apellido,
      roles:    data.roles as RolCodigo[],
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    set({ user })
    // Reemplaza el viejo registerOnLogin: refresca toda la data de la nueva sesión.
    queryClient.invalidateQueries()
  },

  /** Registra un usuario CLIENT y arranca la sesión igual que login. */
  register: async (data) => {
    const res = await registerApi(data)
    const user: AuthUser = {
      id:       res.id,
      email:    res.email,
      nombre:   res.nombre,
      apellido: res.apellido,
      roles:    res.roles as RolCodigo[],
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    set({ user })
    queryClient.invalidateQueries()
  },

  /** Cierra sesión en el backend, limpia el estado local y descarta el cache. */
  logout: async () => {
    await logoutApi()
    localStorage.removeItem(STORAGE_KEY)
    set({ user: null })
    // Descarta toda la data privada cacheada para que no se filtre entre sesiones.
    queryClient.clear()
  },
}))

/**
 * Hook de conveniencia que conserva la API que consumían los componentes
 * (user, login, logout, register) cuando vivía en AuthContext.
 */
export function useAuth() {
  const user = useAuthStore((s) => s.user)
  const login = useAuthStore((s) => s.login)
  const logout = useAuthStore((s) => s.logout)
  const register = useAuthStore((s) => s.register)
  return { user, login, logout, register }
}
