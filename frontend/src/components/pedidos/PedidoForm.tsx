// src/components/pedidos/PedidoForm.tsx
import { useState, useEffect, useMemo } from 'react'
import type { FormEvent } from 'react'
import type { Pedido, PedidoCreate } from '../../models/pedido'
import { usePedidos } from '../../hooks/usePedidos'
import { useProductos } from '../../hooks/useProductos'
import { useDirecciones } from '../../hooks/useDirecciones'
import type { Producto } from '../../models/producto'
import { formatDireccion } from '../../models/direccion'
import type { RolCodigo } from '../../models/auth'
import { listarUsuariosApi, type UsuarioListItem } from '../../api/auth'
import { getDireccionesApi } from '../../api/direcciones'
import { editarPedidoApi } from '../../api/pedidos'
import { ApiError } from '../../api/client'

interface LineaItem { producto: Producto; cantidad: number; personalizacion?: number[] | null }
interface Props {
  roles: RolCodigo[]
  usuarioIdActual: number | null
  onSuccess: () => void
  onClose: () => void
  /** Si se provee, el form trabaja en modo edición */
  initial?: Pedido | null
}

const COSTO_ENVIO = 50

export default function PedidoForm({ roles, usuarioIdActual, onSuccess, onClose, initial }: Props) {
  const { crear, formasPago, recargar } = usePedidos()
  const { productos }         = useProductos()
  const { direcciones: misDirecciones } = useDirecciones()

  const modoEdicion = !!initial
  const puedeCrearParaOtros = roles.includes('ADMIN') || roles.includes('PEDIDOS')

  const [lineas,             setLineas]             = useState<LineaItem[]>([])
  const [formaPago,          setFormaPago]          = useState('')
  const [direccionId,        setDireccionId]        = useState<number | null | 'retiro'>('retiro')
  const [notas,              setNotas]              = useState('')
  const [usuarioIdOverride,  setUsuarioIdOverride]  = useState<number | ''>('')
  const [busqueda,           setBusqueda]           = useState('')
  const [showDropdown,       setShowDropdown]       = useState(false)
  const [direccionesTarget,  setDireccionesTarget]  = useState(misDirecciones)
  const [loadingDirecciones, setLoadingDirecciones] = useState(false)
  const [usuarios,           setUsuarios]           = useState<UsuarioListItem[]>([])
  const [loading,            setLoading]            = useState(false)
  const [error,              setError]              = useState('')

  useEffect(() => {
    if (!puedeCrearParaOtros) return
    listarUsuariosApi(false, undefined, 1, 100).then(res => setUsuarios(res.items)).catch(() => {})
  }, [puedeCrearParaOtros])

  // Pre-llenar en modo edición
  useEffect(() => {
    if (!initial) return
    // Reconstruir lineas desde detalles usando el catálogo actual
    const lineasIniciales: LineaItem[] = initial.detalles.map(d => {
      const prod = productos.find(p => p.id === d.producto_id)
      if (!prod) return null
      return { producto: prod, cantidad: d.cantidad, personalizacion: d.personalizacion }
    }).filter(Boolean) as LineaItem[]
    setLineas(lineasIniciales)
    setFormaPago(initial.forma_pago_codigo)
    setDireccionId(initial.direccion_id ?? 'retiro')
    setNotas(initial.notas ?? '')
  }, [initial, productos])

  useEffect(() => {
    if (!usuarioIdOverride) { setDireccionesTarget(misDirecciones); setDireccionId('retiro'); return }
    const uid = Number(usuarioIdOverride)
    if (uid === usuarioIdActual) { setDireccionesTarget(misDirecciones); setDireccionId('retiro'); return }
    setLoadingDirecciones(true)
    getDireccionesApi(uid).then(res => { setDireccionesTarget(res.items); setDireccionId('retiro') }).catch(() => setDireccionesTarget([])).finally(() => setLoadingDirecciones(false))
  }, [usuarioIdOverride, misDirecciones, usuarioIdActual])

  useEffect(() => {
    const primera = formasPago.find(f => f.habilitado)
    if (primera && !formaPago) setFormaPago(primera.codigo)
  }, [formasPago])

  const productosFiltrados = useMemo(() => {
    if (!busqueda.trim()) return []
    const q = busqueda.toLowerCase()
    const yaAgregados = new Set(lineas.map(l => l.producto.id))
    return productos.filter(p => p.activo && p.disponible && !yaAgregados.has(p.id) && (p.nombre.toLowerCase().includes(q) || p.codigo.toLowerCase().includes(q))).slice(0, 8)
  }, [busqueda, productos, lineas])

  const agregarProducto = (p: Producto) => { setLineas(prev => [...prev, { producto: p, cantidad: 1 }]); setBusqueda(''); setShowDropdown(false) }
  const cambiarCantidad = (idx: number, val: number) => { const v = Math.max(1, Math.min(99, val || 1)); setLineas(prev => prev.map((l, i) => i === idx ? { ...l, cantidad: v } : l)) }
  const removerLinea    = (idx: number) => { setLineas(prev => prev.filter((_, i) => i !== idx)) }

  const subtotal = lineas.reduce((s, l) => s + l.producto.precio_base * l.cantidad, 0)
  const envio    = direccionId !== 'retiro' && direccionId !== null ? COSTO_ENVIO : 0
  const total    = subtotal + envio

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault(); setError('')
    if (lineas.length === 0) { setError('Agregá al menos un producto.'); return }
    if (!formaPago) { setError('Seleccioná una forma de pago.'); return }
    setLoading(true)
    try {
      if (modoEdicion && initial) {
        // Modo edición: PATCH /pedidos/{id}
        await editarPedidoApi(initial.id, {
          forma_pago_codigo: formaPago,
          direccion_id: direccionId === 'retiro' ? null : (direccionId as number),
          notas: notas.trim() || null,
          items: lineas.map(l => ({ producto_id: l.producto.id, cantidad: l.cantidad, personalizacion: l.personalizacion ?? null })),
        })
        recargar()
      } else {
        // Modo creación
        const payload: PedidoCreate = { forma_pago_codigo: formaPago, direccion_id: direccionId === 'retiro' ? null : direccionId, notas: notas.trim() || null, items: lineas.map(l => ({ producto_id: l.producto.id, cantidad: l.cantidad, personalizacion: l.personalizacion ?? null })) }
        if (puedeCrearParaOtros && usuarioIdOverride) payload.usuario_id = Number(usuarioIdOverride)
        await crear(payload)
      }
      onSuccess()
    }
    catch (e) { setError(e instanceof ApiError ? e.message : modoEdicion ? 'Error al actualizar el pedido.' : 'Error al crear el pedido.') }
    finally { setLoading(false) }
  }

  const inputCls = "w-full border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500"
  const labelCls = "block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"

  return (
    <form onSubmit={handleSubmit} className="space-y-6">

      {/* Selector de usuario — solo en modo creación */}
      {!modoEdicion && puedeCrearParaOtros && (
        <div>
          <label className={labelCls}>Cliente <span className="text-gray-400 dark:text-gray-500 font-normal">(opcional — si vacío, se usa tu usuario)</span></label>
          <select value={usuarioIdOverride} onChange={e => setUsuarioIdOverride(e.target.value === '' ? '' : Number(e.target.value))} className={inputCls}>
            <option value="">— Mi usuario —</option>
            {usuarios.map(u => <option key={u.id} value={u.id}>{u.nombre} {u.apellido} ({u.email})</option>)}
          </select>
        </div>
      )}

      {/* Buscador + tabla de items */}
      <div>
        <label className={labelCls}>Productos <span className="text-red-500">*</span></label>
        <div className="relative">
          <input type="text" value={busqueda} onChange={e => { setBusqueda(e.target.value); setShowDropdown(true) }} onFocus={() => setShowDropdown(true)}
            placeholder="Buscar por nombre o código..." className={inputCls} />
          {showDropdown && productosFiltrados.length > 0 && (
            <ul className="absolute z-20 w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-xl shadow-lg mt-1 max-h-52 overflow-auto">
              {productosFiltrados.map(p => (
                <li key={p.id}>
                  <button type="button" onClick={() => agregarProducto(p)}
                    className="w-full flex items-center justify-between px-4 py-2.5 text-sm hover:bg-blue-50 dark:hover:bg-blue-900/20 transition">
                    <span>
                      <span className="font-medium text-gray-800 dark:text-gray-200">{p.nombre}</span>
                      <span className="text-gray-400 dark:text-gray-500 ml-2 text-xs">{p.codigo}</span>
                    </span>
                    <span className="text-gray-600 dark:text-gray-300 font-semibold">${p.precio_base.toFixed(2)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {lineas.length > 0 && (
          <div className="mt-3 border border-gray-200 dark:border-gray-600 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700/50">
                <tr>
                  <th className="text-left px-4 py-2.5 font-medium text-gray-600 dark:text-gray-300">Producto</th>
                  <th className="text-right px-3 py-2.5 font-medium text-gray-600 dark:text-gray-300">Precio</th>
                  <th className="text-center px-3 py-2.5 font-medium text-gray-600 dark:text-gray-300">Cantidad</th>
                  <th className="text-right px-3 py-2.5 font-medium text-gray-600 dark:text-gray-300">Subtotal</th>
                  <th className="px-3 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {lineas.map((l, idx) => (
                  <tr key={l.producto.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/40">
                    <td className="px-4 py-2.5">
                      <span className="font-medium text-gray-800 dark:text-gray-200">{l.producto.nombre}</span>
                      <span className="text-gray-400 dark:text-gray-500 ml-1 text-xs">({l.producto.codigo})</span>
                    </td>
                    <td className="px-3 py-2.5 text-right text-gray-600 dark:text-gray-400">${l.producto.precio_base.toFixed(2)}</td>
                    <td className="px-3 py-2.5 text-center">
                      <input type="number" min={1} max={99} value={l.cantidad} onChange={e => cambiarCantidad(idx, Number(e.target.value))}
                        className="w-16 border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1 text-sm text-center focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200" />
                    </td>
                    <td className="px-3 py-2.5 text-right font-semibold text-gray-800 dark:text-gray-200">${(l.producto.precio_base * l.cantidad).toFixed(2)}</td>
                    <td className="px-3 py-2.5 text-center">
                      <button type="button" onClick={() => removerLinea(idx)} className="text-red-400 hover:text-red-600 transition p-1" title="Quitar">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {lineas.length === 0 && <p className="text-sm text-gray-400 dark:text-gray-500 italic mt-2">Ningún producto agregado todavía.</p>}
      </div>

      {/* Forma de pago */}
      <div>
        <label className={labelCls}>Forma de pago <span className="text-red-500">*</span></label>
        <select value={formaPago} onChange={e => setFormaPago(e.target.value)} required className={inputCls}>
          <option value="">Seleccioná forma de pago...</option>
          {formasPago.filter(f => f.habilitado).map(f => <option key={f.codigo} value={f.codigo}>{f.descripcion}</option>)}
        </select>
      </div>

      {/* Dirección */}
      <div>
        <label className={labelCls}>Dirección de entrega</label>
        {loadingDirecciones
          ? <div className="w-full h-10 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse" />
          : (
            <select value={direccionId === 'retiro' ? 'retiro' : String(direccionId ?? 'retiro')} onChange={e => { const v = e.target.value; setDireccionId(v === 'retiro' ? 'retiro' : Number(v)) }} className={inputCls}>
              <option value="retiro">🏠 Retiro en local (sin costo de envío)</option>
              {direccionesTarget.filter(d => d.activo).map(d => (
                <option key={d.id} value={String(d.id)}>{d.alias ? `${d.alias} — ` : ''}{formatDireccion(d)}{d.es_principal ? ' ⭐' : ''}</option>
              ))}
            </select>
          )
        }
        {direccionId !== 'retiro' && <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">+ ${COSTO_ENVIO} de costo de envío</p>}
      </div>

      {/* Notas */}
      <div>
        <label className={labelCls}>Notas <span className="text-gray-400 dark:text-gray-500 font-normal">(opcional)</span></label>
        <textarea value={notas} onChange={e => setNotas(e.target.value)} rows={2} placeholder="Instrucciones especiales, aclaraciones..."
          className={`${inputCls} resize-none`} />
      </div>

      {/* Resumen */}
      {lineas.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-700/40 rounded-xl p-4 space-y-1.5 text-sm">
          <div className="flex justify-between text-gray-600 dark:text-gray-400"><span>Subtotal</span><span>${subtotal.toFixed(2)}</span></div>
          <div className="flex justify-between text-gray-600 dark:text-gray-400"><span>Envío</span><span>{envio > 0 ? `$${envio.toFixed(2)}` : 'Gratis'}</span></div>
          <div className="flex justify-between font-bold text-gray-800 dark:text-gray-100 pt-1 border-t border-gray-200 dark:border-gray-600"><span>Total</span><span>${total.toFixed(2)}</span></div>
        </div>
      )}

      {error && <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-xl px-4 py-3 text-sm text-red-700 dark:text-red-300">{error}</div>}

      <div className="flex gap-3 pt-2">
        <button type="button" onClick={onClose} className="flex-1 px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition">Cancelar</button>
        <button type="submit" disabled={loading || lineas.length === 0} className="flex-1 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl text-sm font-semibold text-white transition">
          {loading ? (modoEdicion ? 'Actualizando...' : 'Creando...') : (modoEdicion ? 'Actualizar pedido' : 'Crear pedido')}
        </button>
      </div>
    </form>
  )
}
