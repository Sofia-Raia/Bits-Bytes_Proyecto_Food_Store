// src/api/uploads.ts
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface CloudinaryResponse {
  secure_url: string
  public_id: string
  width: number
  height: number
  format: string
  resource_type: string
}

/**
 * Sube una imagen al backend, que la reenvía a Cloudinary (proxy).
 * Devuelve la secure_url y el public_id para guardar/borrar luego.
 * Usa axios "pelado" con multipart: dejamos que el browser arme el
 * Content-Type con su boundary, sin forzar JSON.
 */
export async function subirImagen(file: File, folder = ''): Promise<CloudinaryResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('folder', folder)

  try {
    const res = await axios.post<CloudinaryResponse>(
      `${BASE_URL}/uploads/imagen`,
      form,
      { withCredentials: true },
    )
    return res.data
  } catch (err) {
    let msg = 'No se pudo subir la imagen.'
    if (axios.isAxiosError(err) && err.response) {
      const data = err.response.data as { error?: { message?: string }; detail?: string } | undefined
      msg = data?.error?.message ?? data?.detail ?? msg
    }
    throw new Error(msg)
  }
}

/** Elimina una imagen de Cloudinary por su public_id (solo ADMIN). */
export async function eliminarImagen(publicId: string): Promise<void> {
  try {
    await axios.delete(
      `${BASE_URL}/uploads/imagen/${encodeURIComponent(publicId)}`,
      { withCredentials: true },
    )
  } catch (err) {
    if (axios.isAxiosError(err) && err.response && err.response.status === 204) return
    throw new Error('No se pudo eliminar la imagen.')
  }
}
