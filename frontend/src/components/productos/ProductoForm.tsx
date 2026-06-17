// src/components/productos/ProductoForm.tsx
import { useState, useEffect, useMemo } from 'react'
import ImageUploader from '../ui/ImageUploader'
import type { Producto, ProductoCreate, ProductoUpdate, TipoProducto } from '../../models/producto'
import type { Ingrediente } from '../../models/ingrediente'
import type { Categoria } from '../../models/categoria'

interface IngItemRow { ingrediente_id: number; cantidad: number; es_removible: boolean; es_opcional: boolean }

const TIPOS: { value: TipoProducto; label: string; desc: string }[] = [
  { value: 'TERMINADO',     label: 'Terminado',     desc: 'Producto listo para venta, sin receta' },
  { value: 'MANUFACTURADO', label: 'Manufacturado', desc: 'Se fabrica con ingredientes — requiere receta' },
]

interface Props {
  initial?: Producto | null
  categorias: Categoria[]
  ingredientes: Ingrediente[]
  onSubmit: (data: ProductoCreate | ProductoUpdate) => Promise<void>
  onCancel: () => void
  onDirtyChange?: (dirty: boolean) => void
}

export default function ProductoForm({ initial, categorias, ingredientes, onSubmit, onCancel, onDirtyChange }: Props) {
  const [nombre,        setNombre]       = useState('')
  const [descripcion,   setDesc]         = useState('')
  const [precioBase,    setPrecio]       = useState('')
  const [stockCantidad, setStock]        = useState('0')
  const [disponible,    setDisponible]   = useState(true)
  const [imagenesUrl,   setImagenesUrl]  = useState<string[]>([])
  const [tiempoPrepMin, setTiempoPrepMin]= useState<string>('')
  const [tipo,          setTipo]         = useState<TipoProducto>('TERMINADO')
  const [catSel,        setCatSel]       = useState<Map<number, boolean>>(new Map())
  const [ingItems,      setIngItems]     = useState<IngItemRow[]>([])
  const [margen,        setMargen]       = useState(50)
  const [error,         setError]        = useState('')
  const [submitting,    setSubmitting]   = useState(false)
  const [isDirty,       setIsDirty]      = useState(false)

  useEffect(() => {
    if (initial) {
      setNombre(initial.nombre); setDesc(initial.descripcion ?? ''); setPrecio(String(initial.precio_base))
      setStock(String(initial.stock_cantidad)); setDisponible(initial.disponible)
      setImagenesUrl(initial.imagenes_url ?? [])
      setTiempoPrepMin(initial.tiempo_prep_min != null ? String(initial.tiempo_prep_min) : '')
      setTipo(initial.tipo ?? 'TERMINADO')
      const newCatSel = new Map<number, boolean>(); initial.categorias.forEach(c => newCatSel.set(c.id, c.es_principal)); setCatSel(newCatSel)
      if (initial.tipo === 'MANUFACTURADO') {
        setIngItems(initial.ingredientes.map(i => ({ ingrediente_id: i.id, cantidad: i.cantidad, es_removible: i.es_removible, es_opcional: i.es_opcional })))
      } else {
        setIngItems([])
      }
    } else {
      setNombre(''); setDesc(''); setPrecio(''); setStock('0'); setDisponible(true)
      setImagenesUrl([]); setTiempoPrepMin('')
      setTipo('TERMINADO'); setCatSel(new Map()); setIngItems([]); setMargen(50)
    }
    setError(''); setIsDirty(false); onDirtyChange?.(false)
  }, [initial])

  // Al editar un MANUFACTURADO, reconstruye el margen a partir del precio guardado
  // y el costo de la receta, para que el "precio sugerido" coincida con el precio
  // actual y no se modifique de forma silenciosa al guardar. Efecto aparte para no
  // resetear los demás campos cuando el catálogo de ingredientes carga después.
  useEffect(() => {
    if (!initial || initial.tipo !== 'MANUFACTURADO') return
    const costo = initial.ingredientes.reduce((sum, i) => {
      const ref = ingredientes.find(x => x.id === i.id)
      return sum + (ref?.costo ?? 0) * i.cantidad
    }, 0)
    const precio = Number(initial.precio_base)
    if (costo > 0 && precio > 0) {
      setMargen(Number((((precio / costo) - 1) * 100).toFixed(1)))
    }
  }, [initial, ingredientes])

  const markDirty = () => { setIsDirty(true); onDirtyChange?.(true) }

  // ── Categorías ────────────────────────────────────────────────────────────
  const toggleCategoria = (id: number) => { setCatSel(prev => { const n = new Map(prev); n.has(id) ? n.delete(id) : n.set(id, false); return n }); markDirty() }
  const setPrincipal    = (id: number, val: boolean) => { setCatSel(prev => { const n = new Map(prev); if (val) n.forEach((_, k) => n.set(k, false)); n.set(id, val); return n }); markDirty() }

  // ── Ingredientes MANUFACTURADO ────────────────────────────────────────────
  const ingDisponibles = useMemo(() => ingredientes.filter(i => !ingItems.some(item => item.ingrediente_id === i.id)), [ingredientes, ingItems])

  const handleAddIngrediente = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = Number(e.target.value); if (!id) return
    setIngItems(prev => [...prev, { ingrediente_id: id, cantidad: 1, es_removible: false, es_opcional: false }]); e.target.value = ''; markDirty()
  }
  const updateCantidad   = (idx: number, val: number) => { setIngItems(prev => prev.map((item, i) => i === idx ? { ...item, cantidad: val } : item)); markDirty() }
  const updateRemovible  = (idx: number, val: boolean) => { setIngItems(prev => prev.map((item, i) => i === idx ? { ...item, es_removible: val } : item)); markDirty() }
  const updateOpcional   = (idx: number, val: boolean) => { setIngItems(prev => prev.map((item, i) => i === idx ? { ...item, es_opcional: val } : item)); markDirty() }
  const removeIngItem    = (idx: number) => { setIngItems(prev => prev.filter((_, i) => i !== idx)); markDirty() }
  const handleTipoChange = (newTipo: TipoProducto) => { setTipo(newTipo); setIngItems([]); if (newTipo === 'MANUFACTURADO') setStock('0'); markDirty() }

  // ── Imágenes ─────────────────────────────────────────────────────────────
  const addImagen    = () => { setImagenesUrl(prev => [...prev, '']); markDirty() }
  const setImagen    = (idx: number, val: string) => { setImagenesUrl(prev => prev.map((v, i) => i === idx ? val : v)); markDirty() }
  const removeImagen = (idx: number) => { setImagenesUrl(prev => prev.filter((_, i) => i !== idx)); markDirty() }

  // ── Cálculos ──────────────────────────────────────────────────────────────
  const costoTotal = useMemo(() => {
    if (tipo !== 'MANUFACTURADO') return 0
    return ingItems.reduce((sum, item) => { const ing = ingredientes.find(i => i.id === item.ingrediente_id); return sum + (ing?.costo ?? 0) * item.cantidad }, 0)
  }, [ingItems, ingredientes, tipo])

  const precioSugerido = useMemo(() => costoTotal * (1 + margen / 100), [costoTotal, margen])

  const manufError: string | null = useMemo(() => {
    if (tipo !== 'MANUFACTURADO') return null
    if (ingItems.length === 0) return 'Debe cargar un ingrediente para guardarlo'
    if (ingItems.some(item => item.cantidad <= 0)) return 'Cada ingrediente debe tener cantidad mayor a 0'
    return null
  }, [tipo, ingItems])

  // ── Submit ────────────────────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (nombre.trim().length < 2) { setError('El nombre debe tener al menos 2 caracteres'); return }
    // El precio de un MANUFACTURADO se deriva de la receta (costo × margen);
    // solo el TERMINADO tiene precio cargado manualmente.
    if (tipo === 'TERMINADO' && (!precioBase || Number(precioBase) < 0)) {
      setError('El precio debe ser mayor o igual a 0'); return
    }
    if (catSel.size === 0) { setError('Debe seleccionar al menos una categoría'); return }
    if (Number(stockCantidad) < 0) { setError('El stock no puede ser negativo'); return }
    if (manufError) { setError(manufError); return }
    setError(''); setSubmitting(true)
    try {
      // Un TERMINADO no tiene receta; solo el MANUFACTURADO envía ingredientes.
      const ingPayload = tipo === 'MANUFACTURADO' ? ingItems : []

      const imagenesLimpias = imagenesUrl.map(u => u.trim()).filter(Boolean)

      const precioFinal = tipo === 'MANUFACTURADO'
        ? Number(precioSugerido.toFixed(2))
        : Number(precioBase)

      const data: ProductoCreate = {
        nombre: nombre.trim(),
        descripcion: descripcion.trim() || null,
        precio_base: precioFinal,
        stock_cantidad: tipo === 'MANUFACTURADO' ? 0 : Number(stockCantidad),
        disponible, tipo,
        imagenes_url: imagenesLimpias,
        tiempo_prep_min: tipo === 'MANUFACTURADO' && tiempoPrepMin ? Number(tiempoPrepMin) : null,
        categoria_ids: Array.from(catSel.entries()).sort((a, b) => Number(b[1]) - Number(a[1])).map(([id]) => id),
        ingredientes: ingPayload,
      }
      await onSubmit(data); setIsDirty(false); onDirtyChange?.(false)
    } catch (err: unknown) { setError(err instanceof Error ? err.message : 'Error al guardar') }
    finally { setSubmitting(false) }
  }

  const inputCls = "w-full border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400 text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 placeholder-gray-400 dark:placeholder-gray-500"
  const labelCls = "block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">

      {/* Tipo */}
      <div>
        <label className={`${labelCls} mb-2`}>Tipo de producto <span className="text-red-500">*</span></label>
        <div className="grid grid-cols-2 gap-3">
          {TIPOS.map(t => (
            <label key={t.value} className={`flex flex-col gap-1 p-3 rounded-xl border-2 cursor-pointer transition ${tipo === t.value ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'}`}>
              <div className="flex items-center gap-2">
                <input type="radio" name="tipo" value={t.value} checked={tipo === t.value} onChange={() => handleTipoChange(t.value)} className="accent-blue-600" />
                <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">{t.label}</span>
              </div>
              <span className="text-xs text-gray-500 dark:text-gray-400 pl-5">{t.desc}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Nombre */}
      <div>
        <label className={labelCls}>Nombre <span className="text-red-500">*</span></label>
        <input type="text" value={nombre} onChange={e => { setNombre(e.target.value); markDirty() }} placeholder="Ej: Pizza Margherita" maxLength={150} required className={inputCls} />
      </div>

      {/* Precio + Stock — solo TERMINADO. El MANUFACTURADO deriva su precio
          de la receta (costo × margen) y su stock del de los ingredientes. */}
      {tipo === 'TERMINADO' && (
        <div className="grid gap-4 grid-cols-2">
          <div>
            <label className={labelCls}>Precio base <span className="text-red-500">*</span></label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 text-sm">$</span>
              <input type="number" value={precioBase} onChange={e => { setPrecio(e.target.value); markDirty() }} placeholder="0.00" min="0" step="0.01" required className={`${inputCls} pl-7`} />
            </div>
          </div>
          <div>
            <label className={labelCls}>Stock disponible</label>
            <input type="number" value={stockCantidad} onChange={e => { setStock(e.target.value); markDirty() }} min="0" className={inputCls} />
          </div>
        </div>
      )}

      {/* Tiempo de preparación — solo MANUFACTURADO (un TERMINADO no se prepara). */}
      {tipo === 'MANUFACTURADO' && (
        <div>
          <label className={labelCls}>Tiempo de preparación <span className="text-gray-400 dark:text-gray-500 font-normal">(minutos, opcional)</span></label>
          <input type="number" value={tiempoPrepMin} onChange={e => { setTiempoPrepMin(e.target.value); markDirty() }} min="0" step="1" placeholder="Ej: 15" className={inputCls} />
        </div>
      )}

      {/* Disponible */}
      <label className="flex items-center gap-3 cursor-pointer select-none">
        <input type="checkbox" checked={disponible} onChange={e => { setDisponible(e.target.checked); markDirty() }} className="w-4 h-4 accent-blue-600" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-200">Disponible para pedidos</span>
      </label>

      {/* Descripción */}
      <div>
        <label className={labelCls}>Descripción</label>
        <textarea value={descripcion} onChange={e => { setDesc(e.target.value); markDirty() }} placeholder="Descripción del producto..." rows={2} className={`${inputCls} resize-none`} />
      </div>

      {/* Galería de imágenes */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className={labelCls.replace('mb-1','')}>Imágenes <span className="text-gray-400 dark:text-gray-500 font-normal text-xs ml-1">(URLs — primera = principal)</span></label>
          <button type="button" onClick={addImagen}
            className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 px-2.5 py-1 rounded-lg transition">
            + Agregar
          </button>
          <ImageUploader
            label="Subir imagen"
            folder="productos"
            onUploaded={(url) => setImagenesUrl([...imagenesUrl, url])}
          />
        </div>
        {imagenesUrl.length === 0
          ? <p className="text-xs text-gray-400 dark:text-gray-500 italic">Sin imágenes. Hacé clic en "+ Agregar" para añadir URLs.</p>
          : (
            <div className="flex flex-col gap-2">
              {imagenesUrl.map((url, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 dark:text-gray-500 w-5 flex-shrink-0">{idx + 1}</span>
                  <input type="url" value={url} onChange={e => setImagen(idx, e.target.value)}
                    placeholder="https://ejemplo.com/imagen.jpg"
                    className="flex-1 border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 placeholder-gray-400 dark:placeholder-gray-500" />
                  {url.trim() && (
                    <img src={url.trim()} alt="" className="w-8 h-8 object-cover rounded-lg border border-gray-200 dark:border-gray-600 flex-shrink-0"
                      onError={e => { (e.target as HTMLImageElement).style.opacity = '0.3' }} />
                  )}
                  <button type="button" onClick={() => removeImagen(idx)}
                    className="text-gray-400 hover:text-red-500 dark:hover:text-red-400 w-7 h-7 flex items-center justify-center rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition flex-shrink-0">
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )
        }
      </div>

      {/* Categorías */}
      <div>
        <label className={`${labelCls} mb-2`}>Categorías <span className="text-red-500">*</span> <span className="text-xs text-gray-400 dark:text-gray-500 ml-1">(al menos 1)</span></label>
        {categorias.length === 0
          ? <p className="text-sm text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 rounded-lg">No hay categorías disponibles. Creá una primero.</p>
          : (
            <div className="border border-gray-200 dark:border-gray-600 rounded-xl max-h-40 overflow-y-auto divide-y divide-gray-50 dark:divide-gray-700">
              {categorias.map(c => {
                const checked = catSel.has(c.id); const esPrincipal = catSel.get(c.id) ?? false
                return (
                  <div key={c.id} className="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-700/40">
                    <input type="checkbox" checked={checked} onChange={() => toggleCategoria(c.id)} className="w-4 h-4 accent-blue-600" id={`cat-${c.id}`} />
                    <label htmlFor={`cat-${c.id}`} className="flex-1 text-sm text-gray-700 dark:text-gray-200 cursor-pointer">{c.nombre}</label>
                    {checked && (
                      <label className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 cursor-pointer">
                        <input type="checkbox" checked={esPrincipal} onChange={e => setPrincipal(c.id, e.target.checked)} className="w-3 h-3 accent-yellow-500" />
                        Principal
                      </label>
                    )}
                  </div>
                )
              })}
            </div>
          )
        }
        {catSel.size > 0 && <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">{catSel.size} categoría(s) seleccionada(s)</p>}
      </div>

      {/* Ingredientes MANUFACTURADO */}
      {tipo === 'MANUFACTURADO' && (
        <div className="border border-purple-200 dark:border-purple-700 rounded-xl p-4 bg-purple-50/50 dark:bg-purple-900/10">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-purple-800 dark:text-purple-300">🧪 Receta de ingredientes <span className="text-red-500">*</span></h3>
            <span className="text-xs text-purple-600 dark:text-purple-400">{ingItems.length} ingrediente{ingItems.length !== 1 ? 's' : ''}</span>
          </div>

          {ingDisponibles.length > 0 && (
            <select onChange={handleAddIngrediente} defaultValue=""
              className="w-full border border-purple-200 dark:border-purple-600 rounded-xl px-3 py-2 text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-400 mb-3">
              <option value="">+ Agregar ingrediente...</option>
              {ingDisponibles.map(i => <option key={i.id} value={i.id}>{i.nombre}{i.es_alergeno ? ' ⚠️' : ''} — ${i.costo.toFixed(2)}/{i.unidad_medida}</option>)}
            </select>
          )}
          {ingDisponibles.length === 0 && ingredientes.length > 0 && ingItems.length > 0 && <p className="text-xs text-purple-600 dark:text-purple-400 mb-3">Todos los ingredientes disponibles fueron agregados.</p>}
          {ingredientes.length === 0 && <p className="text-sm text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 rounded-lg mb-3">No hay ingredientes disponibles. Creá uno en la sección de Ingredientes primero.</p>}

          {ingItems.length > 0 && (
            <div className="overflow-x-auto rounded-xl border border-purple-100 dark:border-purple-700 bg-white dark:bg-gray-800">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-purple-50 dark:bg-purple-900/20 border-b border-purple-100 dark:border-purple-700">
                    <th className="text-left px-3 py-2.5 text-xs font-semibold text-purple-700 dark:text-purple-300 uppercase tracking-wide">Ingrediente</th>
                    <th className="text-right px-3 py-2.5 text-xs font-semibold text-purple-700 dark:text-purple-300 uppercase tracking-wide whitespace-nowrap">Costo/u</th>
                    <th className="text-center px-3 py-2.5 text-xs font-semibold text-purple-700 dark:text-purple-300 uppercase tracking-wide">Cantidad</th>
                    <th className="text-right px-3 py-2.5 text-xs font-semibold text-purple-700 dark:text-purple-300 uppercase tracking-wide">Subtotal</th>
                    <th className="text-center px-2 py-2.5 text-xs font-semibold text-purple-700 dark:text-purple-300 uppercase tracking-wide">Remov.</th>
                    <th className="text-center px-2 py-2.5 text-xs font-semibold text-purple-700 dark:text-purple-300 uppercase tracking-wide">Opc.</th>
                    <th className="px-2 py-2.5"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-purple-50 dark:divide-purple-900/30">
                  {ingItems.map((item, idx) => {
                    const ing = ingredientes.find(i => i.id === item.ingrediente_id)
                    const costoU = ing?.costo ?? 0
                    return (
                      <tr key={item.ingrediente_id} className="hover:bg-purple-50/40 dark:hover:bg-purple-900/10">
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-1.5">
                            <span className="font-medium text-gray-800 dark:text-gray-200">{ing?.nombre ?? '?'}</span>
                            {ing?.es_alergeno && <span className="text-xs text-amber-600 dark:text-amber-400">⚠️</span>}
                            <span className="text-xs text-gray-400 dark:text-gray-500">{ing?.unidad_medida}</span>
                          </div>
                        </td>
                        <td className="px-3 py-2.5 text-right text-gray-600 dark:text-gray-400 whitespace-nowrap">${costoU.toFixed(2)}</td>
                        <td className="px-3 py-2.5 text-center">
                          <input type="number" value={item.cantidad} onChange={e => updateCantidad(idx, Number(e.target.value))} step="0.01" min="0.01"
                            className={`w-24 text-center border rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 ${item.cantidad <= 0 ? 'border-red-300 focus:ring-red-300' : 'border-gray-200 dark:border-gray-600 focus:ring-purple-300'}`} />
                        </td>
                        <td className="px-3 py-2.5 text-right font-medium text-gray-800 dark:text-gray-200 whitespace-nowrap">${(costoU * item.cantidad).toFixed(2)}</td>
                        <td className="px-2 py-2.5 text-center">
                          <input type="checkbox" checked={item.es_removible} onChange={e => updateRemovible(idx, e.target.checked)}
                            className="w-4 h-4 accent-green-500" title="Removible: el cliente puede pedirlo sin este ingrediente" />
                        </td>
                        <td className="px-2 py-2.5 text-center">
                          <input type="checkbox" checked={item.es_opcional} onChange={e => updateOpcional(idx, e.target.checked)}
                            className="w-4 h-4 accent-amber-500" title="Opcional: el cliente puede pedirlo como extra adicional" />
                        </td>
                        <td className="px-2 py-2.5 text-center">
                          <button type="button" onClick={() => removeIngItem(idx)} className="text-gray-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 w-7 h-7 rounded-lg flex items-center justify-center transition text-xs font-bold mx-auto" title="Eliminar">✕</button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {manufError && <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg px-3 py-2 mt-3">⚠️ {manufError}</p>}

          {ingItems.length > 0 && (
            <div className="mt-4 pt-4 border-t border-purple-200 dark:border-purple-700 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">Costo total de receta:</span>
                <span className="text-base font-bold text-purple-700 dark:text-purple-300">${costoTotal.toFixed(2)}</span>
              </div>
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-200 whitespace-nowrap">Margen (%):</label>
                <input type="number" value={margen} onChange={e => setMargen(Number(e.target.value))} min="0" step="0.1"
                  className="w-28 border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200" />
              </div>
              <div className="flex items-center justify-between bg-purple-100 dark:bg-purple-900/30 rounded-xl px-4 py-3">
                <div>
                  <p className="text-xs text-purple-600 dark:text-purple-400 font-medium uppercase tracking-wide">Precio de venta</p>
                  <p className="text-xl font-bold text-purple-800 dark:text-purple-200">${precioSugerido.toFixed(2)}</p>
                  <p className="text-xs text-purple-500 dark:text-purple-400">= ${costoTotal.toFixed(2)} × (1 + {margen}%)</p>
                </div>
                <span className="text-xs text-purple-500 dark:text-purple-400 max-w-[140px] text-right">Calculado automáticamente desde la receta y el margen.</span>
              </div>
            </div>
          )}
        </div>
      )}

      {error && <p className="text-sm text-red-500 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg px-3 py-2">{error}</p>}

      <div className="flex gap-3 justify-end pt-2">
        <button type="button" onClick={onCancel} className="px-5 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-xl transition">Cancelar</button>
        <button type="submit" disabled={submitting || !!manufError} className="px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed">
          {submitting ? 'Guardando...' : initial ? 'Guardar cambios' : 'Crear producto'}
        </button>
      </div>
    </form>
  )
}
