// src/components/ingredientes/IngredienteForm.tsx

import { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { Ingrediente, IngredienteCreate, IngredienteUpdate } from '../../models/ingrediente'
import { getUnidadesMedidaApi } from '../../api/ingredientes'



interface Props {
  initial?: Ingrediente | null
  loading?: boolean
  onSubmit: (data: IngredienteCreate | IngredienteUpdate) => Promise<void>
  onCancel: () => void
  onDirtyChange?: (dirty: boolean) => void
}

export default function IngredienteForm({ initial, loading = false, onSubmit, onCancel, onDirtyChange }: Props) {
  const [nombre,       setNombre]       = useState('')
  const [descripcion,  setDescripcion]  = useState('')
  const [esAlergeno,   setEsAlergeno]   = useState(false)
  const [costo,        setCosto]        = useState('0')
  const [unidadMedida, setUnidadMedida] = useState<string>('UNIDADES')
  const [stockCantidad,setStockCantidad]= useState('0')
  const [error,        setError]        = useState('')
  const [submitting,   setSubmitting]   = useState(false)

  useEffect(() => {
    setNombre(initial?.nombre ?? ''); setDescripcion(initial?.descripcion ?? '')
    setEsAlergeno(initial?.es_alergeno ?? false); setCosto(String(initial?.costo ?? 0))
    setUnidadMedida(initial?.unidad_medida ?? 'UNIDADES')
    setStockCantidad(String(initial?.stock_cantidad ?? 0)); setError('')
  }, [initial])

  // Catálogo de unidades desde el backend (casi inmutable → se cachea).
  const { data: unidades = [] } = useQuery({
    queryKey: ['unidades-medida'],
    queryFn: getUnidadesMedidaApi,
    staleTime: Infinity,
  })

  // Si el código actual no existe en el catálogo (y no estamos editando), caer en el primero.
  useEffect(() => {
    if (initial || unidades.length === 0) return
    if (!unidades.some(u => u.codigo === unidadMedida)) {
      setUnidadMedida(unidades[0].codigo)
    }
  }, [unidades, initial, unidadMedida])

  const unidadSel = unidades.find(u => u.codigo === unidadMedida)

  const isDirty = useMemo(() => {
    if (!initial) return nombre.trim() !== '' || descripcion.trim() !== '' || esAlergeno !== false || Number(costo) !== 0 || unidadMedida !== 'UNIDADES' || Number(stockCantidad) !== 0
    return nombre.trim() !== initial.nombre || (descripcion.trim() || null) !== (initial.descripcion ?? null) || esAlergeno !== initial.es_alergeno || Number(costo) !== initial.costo || unidadMedida !== initial.unidad_medida || Number(stockCantidad) !== initial.stock_cantidad
  }, [nombre, descripcion, esAlergeno, costo, unidadMedida, stockCantidad, initial])

  useEffect(() => { onDirtyChange?.(isDirty) }, [isDirty, onDirtyChange])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (nombre.trim().length < 2) { setError('El nombre debe tener al menos 2 caracteres'); return }
    if (nombre.trim().length > 100) { setError('El nombre no puede superar 100 caracteres'); return }
    if (Number(costo) < 0) { setError('El costo no puede ser negativo'); return }
    setError(''); setSubmitting(true)
    try {
      await onSubmit({ nombre: nombre.trim(), descripcion: descripcion.trim() || null, es_alergeno: esAlergeno, costo: Number(costo), unidad_medida: unidadMedida, stock_cantidad: Number(stockCantidad) })
      onDirtyChange?.(false)
    } catch (err: unknown) { setError(err instanceof Error ? err.message : 'Error al guardar') }
    finally { setSubmitting(false) }
  }

  const inputCls = "w-full border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400 text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 placeholder-gray-400 dark:placeholder-gray-500"
  const labelCls = "block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div>
        <label className={labelCls}>Nombre <span className="text-red-500">*</span></label>
        <input type="text" value={nombre} onChange={e => setNombre(e.target.value)} placeholder="Ej: Harina de trigo" maxLength={100} required className={inputCls} />
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{nombre.length}/100</p>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelCls}>Costo por unidad <span className="text-red-500">*</span></label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 text-sm">$</span>
            <input type="number" value={costo} onChange={e => setCosto(e.target.value)} placeholder="0.00" min="0" step="0.01" required className={`${inputCls} pl-7`} />
          </div>
        </div>
        <div>
          <label className={labelCls}>Unidad de medida <span className="text-red-500">*</span></label>
          <select value={unidadMedida} onChange={e => setUnidadMedida(e.target.value)} className={inputCls}>
            {unidades.length === 0 && <option value={unidadMedida}>{unidadMedida}</option>}
            {unidades.map(u => <option key={u.id} value={u.codigo}>{u.nombre} ({u.simbolo})</option>)}
          </select>
        </div>
      </div>
      <div>
        <label className={labelCls}>Stock inicial</label>
        <input type="number" value={stockCantidad} onChange={e => setStockCantidad(e.target.value)} placeholder="0.000" min="0" step="0.001" className={inputCls} />
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">Cantidad disponible en {unidadSel?.nombre ?? unidadMedida}. Para ajustar stock más tarde usá "Reponer stock".</p>
      </div>
      <div>
        <label className={labelCls}>Descripción</label>
        <textarea value={descripcion} onChange={e => setDescripcion(e.target.value)} placeholder="Descripción opcional..." rows={3} className={`${inputCls} resize-none`} />
      </div>
      <label className="flex items-center gap-3 cursor-pointer select-none">
        <input type="checkbox" checked={esAlergeno} onChange={e => setEsAlergeno(e.target.checked)} className="w-4 h-4 accent-blue-600" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
          Es alérgeno <span className="ml-1 text-xs text-gray-400 dark:text-gray-500">(se mostrará con advertencia en productos)</span>
        </span>
      </label>
      {error && <p className="text-sm text-red-500 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg px-3 py-2">{error}</p>}
      <div className="flex gap-3 justify-end pt-2">
        <button type="button" onClick={onCancel} className="px-5 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-xl transition">Cancelar</button>
        <button type="submit" disabled={submitting || loading} className="px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition disabled:opacity-50">
          {submitting ? 'Guardando...' : initial ? 'Guardar cambios' : 'Crear ingrediente'}
        </button>
      </div>
    </form>
  )
}
