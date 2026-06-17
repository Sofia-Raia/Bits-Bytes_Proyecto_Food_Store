// src/components/categorias/CategoriaForm.tsx
import { useState, useEffect } from 'react'
import ImageUploader from '../ui/ImageUploader'
import type { Categoria, CategoriaCreate, CategoriaUpdate } from '../../models/categoria'

interface Props {
  initial?: Categoria | null
  categorias: Categoria[]
  onSubmit: (data: CategoriaCreate | CategoriaUpdate) => Promise<void>
  onCancel: () => void
}

export default function CategoriaForm({ initial, categorias, onSubmit, onCancel }: Props) {
  const [nombre,      setNombre]      = useState('')
  const [descripcion, setDesc]        = useState('')
  const [imagenUrl,   setImagenUrl]   = useState('')
  const [parentId,    setParentId]    = useState<string>('')
  const [error,       setError]       = useState('')
  const [submitting,  setSubmitting]  = useState(false)

  useEffect(() => {
    setNombre(initial?.nombre ?? ''); setDesc(initial?.descripcion ?? '')
    setImagenUrl(initial?.imagen_url ?? ''); setParentId(initial?.parent_id != null ? String(initial.parent_id) : '')
    setError('')
  }, [initial])

  const posiblesPadres = categorias.filter(c => c.id !== initial?.id)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (nombre.trim().length < 2) { setError('El nombre debe tener al menos 2 caracteres'); return }
    setError(''); setSubmitting(true)
    try {
      await onSubmit({ nombre: nombre.trim(), descripcion: descripcion.trim() || null, imagen_url: imagenUrl.trim() || null, parent_id: parentId ? Number(parentId) : null })
    } catch (err: unknown) { setError(err instanceof Error ? err.message : 'Error al guardar') }
    finally { setSubmitting(false) }
  }

  const inputCls = "w-full border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400 text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 placeholder-gray-400 dark:placeholder-gray-500"
  const labelCls = "block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div>
        <label className={labelCls}>Nombre <span className="text-red-500">*</span></label>
        <input type="text" value={nombre} onChange={e => setNombre(e.target.value)} placeholder="Ej: Bebidas" maxLength={100} required className={inputCls} />
      </div>
      <div>
        <label className={labelCls}>Categoría padre</label>
        <select value={parentId} onChange={e => setParentId(e.target.value)} className={inputCls}>
          <option value="">— Sin padre (categoría raíz) —</option>
          {posiblesPadres.map(c => <option key={c.id} value={c.id}>{c.parent_id ? `  ↳ ${c.nombre}` : c.nombre}</option>)}
        </select>
      </div>
      <div>
        <label className={labelCls}>Descripción</label>
        <textarea value={descripcion} onChange={e => setDesc(e.target.value)} placeholder="Descripción opcional..." rows={2} className={`${inputCls} resize-none`} />
      </div>
      <div>
        <label className={labelCls}>URL de imagen</label>
        <input type="url" value={imagenUrl} onChange={e => setImagenUrl(e.target.value)} placeholder="https://..." className={inputCls} />
        <div className="flex items-center gap-3 mt-2">
          <ImageUploader label="Subir imagen" folder="categorias" onUploaded={setImagenUrl} />
          {imagenUrl.trim() && (
            <img src={imagenUrl.trim()} alt="" className="w-10 h-10 object-cover rounded-lg border border-gray-200 dark:border-gray-600"
              onError={e => { (e.target as HTMLImageElement).style.opacity = '0.3' }} />
          )}
        </div>
      </div>
      {error && <p className="text-sm text-red-500 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg px-3 py-2">{error}</p>}
      <div className="flex gap-3 justify-end pt-2">
        <button type="button" onClick={onCancel} className="px-5 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-xl transition">Cancelar</button>
        <button type="submit" disabled={submitting} className="px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition disabled:opacity-50">
          {submitting ? 'Guardando...' : initial ? 'Guardar cambios' : 'Crear categoría'}
        </button>
      </div>
    </form>
  )
}
