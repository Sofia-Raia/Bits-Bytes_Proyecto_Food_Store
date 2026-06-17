// src/store/uiStore.ts
import { create } from 'zustand'

export type ToastType = 'success' | 'error' | 'info'

export interface ToastData {
  id: number
  type: ToastType
  message: string
}

const THEME_KEY = 'theme'
const MAX_TOASTS = 3

// Contador monotónico para ids de toast (fuera del estado: no necesita reactividad).
let _nextId = 1

/** Lee el tema persistido y aplica la clase `dark` al <html> antes del primer render. */
function initialDark(): boolean {
  const dark = localStorage.getItem(THEME_KEY) === 'dark'
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('dark', dark)
  }
  return dark
}

interface UiState {
  dark: boolean
  toasts: ToastData[]
  setTheme: (dark: boolean) => void
  toggleTheme: () => void
  addToast: (message: string, type?: ToastType) => void
  removeToast: (id: number) => void
}

export const useUiStore = create<UiState>((set, get) => ({
  dark: initialDark(),
  toasts: [],

  /** Aplica el tema al DOM, lo persiste y actualiza el estado. */
  setTheme: (dark) => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem(THEME_KEY, dark ? 'dark' : 'light')
    set({ dark })
  },

  /** Alterna entre claro y oscuro. */
  toggleTheme: () => get().setTheme(!get().dark),

  /** Encola un toast respetando el límite de stack (descarta los más viejos). */
  addToast: (message, type = 'info') =>
    set((state) => {
      const next = [...state.toasts, { id: _nextId++, type, message }]
      return { toasts: next.length > MAX_TOASTS ? next.slice(next.length - MAX_TOASTS) : next }
    }),

  /** Quita un toast por id. */
  removeToast: (id) =>
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}))

/** Hook de conveniencia para el tema, con la API que usaba TemaContext. */
export function useTheme() {
  const dark = useUiStore((s) => s.dark)
  const toggleTheme = useUiStore((s) => s.toggleTheme)
  return { dark, toggleTheme }
}
