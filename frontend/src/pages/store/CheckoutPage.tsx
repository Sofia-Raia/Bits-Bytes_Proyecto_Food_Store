// src/pages/store/CheckoutPage.tsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCarrito } from '../../store/carritoStore'
import { getDireccionesApi } from '../../api/direcciones'
import { getFormasPagoPublicApi, createPedidoApi, getPedidoConfigApi } from '../../api/pedidos'
import type { Direccion } from '../../models/direccion'
import type { FormaPago, PedidoCreate } from '../../models/pedido'
import Toast, { useToast } from '../../components/ui/Toast'
import { qk } from '../../queries/keys'
import { crearPreferenciaApi } from '../../api/pagos'

function formatPrecio(n: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)
}

export default function CheckoutPage() {
  const qc = useQueryClient()
  const { items, totalPrecio, vaciarCarrito } = useCarrito()
  const navigate = useNavigate()
  const { toasts, addToast, removeToast } = useToast()

  const [direccionId,       setDireccionId]       = useState<number | null>(null)
  const [formaPagoCodigo,   setFormaPagoCodigo]   = useState('')
  const [notas,             setNotas]             = useState('')
  const [errorSubmit,       setErrorSubmit]       = useState('')

  // Si carrito vacío, redirigir a tienda
  useEffect(() => {
    if (items.length === 0) navigate('/store', { replace: true })
  }, [items.length, navigate])

  // Cargar datos del checkout en paralelo
  const direccionesQuery = useQuery({
    queryKey: qk.direcciones.list(),
    queryFn: () => getDireccionesApi(),
  })
  const formasPagoQuery = useQuery({
    queryKey: qk.pedidos.formasPago,
    queryFn: () => getFormasPagoPublicApi(),
  })
  const configQuery = useQuery({
    queryKey: qk.pedidos.config,
    queryFn: () => getPedidoConfigApi(),
    staleTime: 1000 * 60 * 60,  // el costo de envío cambia rara vez
  })

  const direcciones: Direccion[] = direccionesQuery.data?.items ?? []
  const formasPago: FormaPago[] = formasPagoQuery.data ?? []
  const loadingData = direccionesQuery.isLoading || formasPagoQuery.isLoading || configQuery.isLoading
  const errorData = (direccionesQuery.error || formasPagoQuery.error)
    ? 'Error al cargar datos del checkout.'
    : ''

  // Pre-seleccionar la primera forma de pago habilitada cuando llegan los datos
  useEffect(() => {
    if (!formaPagoCodigo) {
      const primera = formasPago.find(f => f.habilitado)
      if (primera) setFormaPagoCodigo(primera.codigo)
    }
  }, [formasPago, formaPagoCodigo])

  // Costo de envío: fuente de verdad en el backend (lo que MercadoPago cobra).
  const costoEnvioBase = Number(configQuery.data?.costo_envio ?? 0)
  const costoEnvio = direccionId !== null ? costoEnvioBase : 0
  const total = totalPrecio + costoEnvio

  const crearMut = useMutation({
    mutationFn: (data: PedidoCreate) => createPedidoApi(data),
    onError: (err: unknown) => {
      setErrorSubmit(err instanceof Error ? err.message : 'Error al crear el pedido.')
    },
  })

  const handleConfirmar = async () => {
    if (!formaPagoCodigo) {
      setErrorSubmit('Seleccioná una forma de pago.')
      return
    }
    setErrorSubmit('')
    try {
      const pedido = await crearMut.mutateAsync({
        forma_pago_codigo: formaPagoCodigo,
        direccion_id:      direccionId,
        notas:             notas.trim() || null,
        items:             items.map(i => ({ producto_id: i.producto_id, cantidad: i.cantidad })),
      })
      qc.invalidateQueries({ queryKey: qk.pedidos.all })

      // Pago con MercadoPago: crear preferencia y redirigir a Checkout Pro
      if (formaPagoCodigo === 'MERCADOPAGO') {
        const { init_point } = await crearPreferenciaApi(pedido.id)
        if (init_point) {
          vaciarCarrito()
          window.location.href = init_point
          return
        }
        // Sin init_point (MP mal configurado): seguir a mis-pedidos
        navigate('/store/mis-pedidos')
        vaciarCarrito()
        addToast('Pedido creado. Completá el pago desde "Mis pedidos".', 'success')
        return
      }

      // Otras formas de pago (efectivo / transferencia)
      navigate('/store/mis-pedidos')
      vaciarCarrito()
      addToast('¡Pedido creado con éxito!', 'success')
    } catch {
      /* el error se refleja vía onError */
    }
  }

  if (loadingData) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
        <div className="h-40 bg-gray-100 dark:bg-gray-700 rounded-2xl" />
        <div className="h-20 bg-gray-100 dark:bg-gray-700 rounded-2xl" />
      </div>
    )
  }

  if (errorData) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-xl p-4 text-red-700 dark:text-red-300 text-sm">
          {errorData}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-6">🧾 Confirmar pedido</h1>

      <div className="grid md:grid-cols-2 gap-6">
        {/* ── Panel izquierdo: resumen + opciones ── */}
        <div className="flex flex-col gap-5">

          {/* Dirección */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-5">
            <h2 className="font-semibold text-gray-700 dark:text-gray-300 mb-3">📍 Dirección de entrega</h2>
            <select
              value={direccionId ?? ''}
              onChange={e => setDireccionId(e.target.value ? Number(e.target.value) : null)}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2.5 text-sm
                bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100
                focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              <option value="">Retiro en local (sin cargo)</option>
              {direcciones.map(d => (
                <option key={d.id} value={d.id}>
                  {d.alias ? `${d.alias} — ` : ''}{d.linea1}, {d.ciudad}
                  {d.es_principal ? ' (principal)' : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Forma de pago */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-5">
            <h2 className="font-semibold text-gray-700 dark:text-gray-300 mb-3">💳 Forma de pago</h2>
            <select
              value={formaPagoCodigo}
              onChange={e => setFormaPagoCodigo(e.target.value)}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2.5 text-sm
                bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100
                focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              <option value="">Seleccioná...</option>
              {formasPago.filter(f => f.habilitado).map(f => (
                <option key={f.codigo} value={f.codigo}>{f.descripcion}</option>
              ))}
            </select>
          </div>

          {/* Notas */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-5">
            <h2 className="font-semibold text-gray-700 dark:text-gray-300 mb-3">📝 Notas (opcional)</h2>
            <textarea
              value={notas}
              onChange={e => setNotas(e.target.value)}
              maxLength={500}
              rows={3}
              placeholder="Instrucciones especiales, alergias, etc."
              className="w-full border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2 text-sm
                bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100
                placeholder-gray-400 dark:placeholder-gray-500
                focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
            />
            <p className="text-xs text-gray-400 dark:text-gray-500 text-right mt-1">{notas.length}/500</p>
          </div>
        </div>

        {/* ── Panel derecho: resumen de items + totales ── */}
        <div className="flex flex-col gap-5">
          <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-5">
            <h2 className="font-semibold text-gray-700 dark:text-gray-300 mb-3">🛒 Resumen</h2>
            <ul className="divide-y divide-gray-50 dark:divide-gray-700 text-sm">
              {items.map(item => (
                <li key={item.producto_id} className="flex justify-between py-2 text-gray-700 dark:text-gray-300">
                  <span className="truncate pr-2">{item.nombre} × {item.cantidad}</span>
                  <span className="font-medium shrink-0">{formatPrecio(item.precio_base * item.cantidad)}</span>
                </li>
              ))}
            </ul>

            <div className="border-t border-gray-100 dark:border-gray-700 mt-3 pt-3 space-y-1 text-sm">
              <div className="flex justify-between text-gray-600 dark:text-gray-400">
                <span>Subtotal</span>
                <span>{formatPrecio(totalPrecio)}</span>
              </div>
              <div className="flex justify-between text-gray-600 dark:text-gray-400">
                <span>Envío</span>
                <span>{costoEnvio === 0 ? 'Sin cargo' : formatPrecio(costoEnvio)}</span>
              </div>
              <div className="flex justify-between font-bold text-gray-800 dark:text-gray-100 text-base pt-1">
                <span>Total</span>
                <span className="text-blue-700 dark:text-blue-400">{formatPrecio(total)}</span>
              </div>
            </div>
          </div>

          {errorSubmit && (
            <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-xl p-3 text-red-700 dark:text-red-300 text-sm">
              {errorSubmit}
            </div>
          )}

          <button
            onClick={handleConfirmar}
            disabled={crearMut.isPending}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-2xl transition disabled:opacity-50 text-sm"
          >
            {crearMut.isPending ? 'Procesando...' : '✅ Confirmar pedido'}
          </button>
        </div>
      </div>

      <Toast toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
