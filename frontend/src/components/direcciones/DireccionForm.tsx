// src/components/direcciones/DireccionForm.tsx
import { useState, useEffect } from 'react'
import type { FormEvent } from 'react'
import type { Direccion, DireccionCreate, DireccionUpdate } from '../../models/direccion'
import { useDirecciones } from '../../hooks/useDirecciones'
import { ApiError } from '../../api/client'

interface Props {
  direccion?: Direccion | null
  onSuccess: () => void
  onClose: () => void
}

export default function DireccionForm({ direccion, onSuccess, onClose }: Props) {
  const { agregar, editar } = useDirecciones()
  const modoEdicion = !!direccion

  const [alias,        setAlias]        = useState(direccion?.alias ?? '')
  const [linea1,       setLinea1]       = useState(direccion?.linea1 ?? '')
  const [linea2,       setLinea2]       = useState(direccion?.linea2 ?? '')
  const [ciudad,       setCiudad]       = useState(direccion?.ciudad ?? '')
  const [provincia,    setProvincia]    = useState(direccion?.provincia ?? '')
  const [codigoPostal, setCodigoPostal] = useState(direccion?.codigo_postal ?? '')
  const [esPrincipal,  setEsPrincipal]  = useState(direccion?.es_principal ?? false)
  const [loading,      setLoading]      = useState(false)
  const [error,        setError]        = useState('')

  useEffect(() => {
    if (direccion) {
      setAlias(direccion.alias ?? ''); setLinea1(direccion.linea1); setLinea2(direccion.linea2 ?? '')
      setCiudad(direccion.ciudad); setProvincia(direccion.provincia ?? ''); setCodigoPostal(direccion.codigo_postal ?? '')
      setEsPrincipal(direccion.es_principal)
    }
  }, [direccion])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault(); setError('')
    if (!linea1.trim()) { setError('La dirección (línea 1) es requerida.'); return }
    if (!ciudad.trim())  { setError('La ciudad es requerida.'); return }
    const payload: DireccionCreate | DireccionUpdate = {
      alias: alias.trim() || null, linea1: linea1.trim(), linea2: linea2.trim() || null,
      ciudad: ciudad.trim(), provincia: provincia.trim() || null, codigo_postal: codigoPostal.trim() || null, es_principal: esPrincipal,
    }
    setLoading(true)
    try {
      if (modoEdicion && direccion) await editar(direccion.id, payload as DireccionUpdate)
      else await agregar(payload as DireccionCreate)
      onSuccess()
    } catch (e) { setError(e instanceof ApiError ? e.message : 'Error al guardar la dirección.') }
    finally { setLoading(false) }
  }

  const inputCls = "w-full border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500"
  const labelCls = "block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className={labelCls}>Alias <span className="text-gray-400 dark:text-gray-500 font-normal">(ej: "Casa", "Trabajo")</span></label>
        <input type="text" value={alias} onChange={e => setAlias(e.target.value)} maxLength={50} placeholder="Casa" className={inputCls} />
      </div>
      <div>
        <label className={labelCls}>Dirección <span className="text-red-500">*</span></label>
        <input type="text" value={linea1} onChange={e => setLinea1(e.target.value)} placeholder="Av. Corrientes 1234" required className={inputCls} />
      </div>
      <div>
        <label className={labelCls}>Piso / Depto <span className="text-gray-400 dark:text-gray-500 font-normal">(opcional)</span></label>
        <input type="text" value={linea2} onChange={e => setLinea2(e.target.value)} placeholder="Piso 3, Depto B" className={inputCls} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>Ciudad <span className="text-red-500">*</span></label>
          <input type="text" value={ciudad} onChange={e => setCiudad(e.target.value)} placeholder="Buenos Aires" required className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>Provincia</label>
          <input type="text" value={provincia} onChange={e => setProvincia(e.target.value)} placeholder="CABA" className={inputCls} />
        </div>
      </div>
      <div>
        <label className={labelCls}>Código postal</label>
        <input type="text" value={codigoPostal} onChange={e => setCodigoPostal(e.target.value)} maxLength={10} placeholder="C1043AAZ" className={inputCls} />
      </div>
      <label className="flex items-center gap-3 cursor-pointer p-3 rounded-xl border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/40 transition">
        <input type="checkbox" checked={esPrincipal} onChange={e => setEsPrincipal(e.target.checked)} className="w-4 h-4 accent-blue-600" />
        <div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-200">Marcar como dirección principal</p>
          <p className="text-xs text-gray-400 dark:text-gray-500">Se usará por defecto en nuevos pedidos</p>
        </div>
      </label>
      {error && <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-xl px-4 py-3 text-sm text-red-700 dark:text-red-300">{error}</div>}
      <div className="flex gap-3 pt-2">
        <button type="button" onClick={onClose} className="flex-1 px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition">Cancelar</button>
        <button type="submit" disabled={loading} className="flex-1 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 rounded-xl text-sm font-semibold text-white transition">
          {loading ? 'Guardando...' : modoEdicion ? 'Guardar cambios' : 'Agregar dirección'}
        </button>
      </div>
    </form>
  )
}
