// src/components/ui/ImageUploader.tsx
import { useRef, useState, type ChangeEvent } from 'react'
import { subirImagen } from '../../api/uploads'

interface Props {
  /** Se invoca con la secure_url de Cloudinary al terminar la subida. */
  onUploaded: (url: string) => void
  /** Subcarpeta destino en Cloudinary (ej: 'productos', 'categorias'). */
  folder?: string
  label?: string
}

/**
 * Botón de subida de imagen. Envía el archivo al backend (módulo uploads), que lo
 * sube a Cloudinary y devuelve la URL. Muestra estado de carga y errores.
 */
export default function ImageUploader({ onUploaded, folder = '', label = 'Subir imagen' }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setError('')
    setLoading(true)
    try {
      const res = await subirImagen(file, folder)
      onUploaded(res.secure_url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo subir la imagen.')
    } finally {
      setLoading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div className="space-y-1">
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
        onChange={handleFile}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={loading}
        className="inline-flex items-center gap-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-60 transition-colors"
      >
        {loading ? 'Subiendo…' : `📤 ${label}`}
      </button>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </div>
  )
}
