// src/lib/queryClient.ts
import { QueryClient } from '@tanstack/react-query'

/**
 * Instancia única de QueryClient para toda la app.
 *
 * Se exporta como singleton (en vez de crearse dentro de un componente) porque
 * los stores de Zustand (authStore, wsStore, pagoStore) necesitan invalidar
 * queries de forma imperativa, fuera del árbol de React.
 *
 * Defaults conservadores para acercarse al comportamiento de la Versión B:
 * - staleTime moderado para evitar refetches innecesarios entre navegaciones.
 * - refetchOnWindowFocus desactivado (la sincronización fina llega por WS).
 * - retry 1: un reintento ante fallos transitorios de red.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})
