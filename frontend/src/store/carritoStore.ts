// src/store/carritoStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ItemCarrito } from '../models/carrito'
import type { Producto } from '../models/producto'

interface CarritoState {
  items: ItemCarrito[]
  agregarItem: (producto: Producto, cantidad?: number) => void
  quitarItem: (producto_id: number) => void
  cambiarCantidad: (producto_id: number, cantidad: number) => void
  vaciarCarrito: () => void
}

export const useCarritoStore = create<CarritoState>()(
  // persist sincroniza los items al localStorage bajo la clave "carrito".
  persist(
    (set) => ({
      items: [],

      /** Suma cantidad si el producto ya está; si no, lo agrega como línea nueva. */
      agregarItem: (producto, cantidad = 1) =>
        set((state) => {
          const existente = state.items.find((i) => i.producto_id === producto.id)
          if (existente) {
            return {
              items: state.items.map((i) =>
                i.producto_id === producto.id
                  ? { ...i, cantidad: i.cantidad + cantidad }
                  : i,
              ),
            }
          }
          return {
            items: [
              ...state.items,
              {
                producto_id: producto.id,
                nombre: producto.nombre,
                precio_base: producto.precio_base,
                cantidad,
                imagen_url: producto.imagenes_url?.[0] ?? null,
              },
            ],
          }
        }),

      /** Quita una línea del carrito por producto_id. */
      quitarItem: (producto_id) =>
        set((state) => ({ items: state.items.filter((i) => i.producto_id !== producto_id) })),

      /** Fija la cantidad de una línea; si baja a 0 o menos, la quita. */
      cambiarCantidad: (producto_id, cantidad) =>
        set((state) => {
          if (cantidad <= 0) {
            return { items: state.items.filter((i) => i.producto_id !== producto_id) }
          }
          return {
            items: state.items.map((i) =>
              i.producto_id === producto_id ? { ...i, cantidad } : i,
            ),
          }
        }),

      /** Vacía el carrito por completo. */
      vaciarCarrito: () => set({ items: [] }),
    }),
    { name: 'carrito' },
  ),
)

/**
 * Hook de conveniencia: expone los items, las acciones y los totales derivados,
 * conservando la API que consumían los componentes desde CarritoContext.
 */
export function useCarrito() {
  const items = useCarritoStore((s) => s.items)
  const agregarItem = useCarritoStore((s) => s.agregarItem)
  const quitarItem = useCarritoStore((s) => s.quitarItem)
  const cambiarCantidad = useCarritoStore((s) => s.cambiarCantidad)
  const vaciarCarrito = useCarritoStore((s) => s.vaciarCarrito)

  const totalItems = items.reduce((acc, i) => acc + i.cantidad, 0)
  const totalPrecio = items.reduce((acc, i) => acc + i.precio_base * i.cantidad, 0)

  return { items, totalItems, totalPrecio, agregarItem, quitarItem, cambiarCantidad, vaciarCarrito }
}
