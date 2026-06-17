// src/models/carrito.ts

export interface ItemCarrito {
  producto_id: number
  nombre: string
  precio_base: number
  cantidad: number
  imagen_url: string | null
}

export interface CarritoState {
  items: ItemCarrito[]
}
