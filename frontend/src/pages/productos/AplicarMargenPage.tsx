// src/pages/productos/AplicarMargenPage.tsx
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getProductosApi } from '../../api/productos'
import { useCategorias } from '../../hooks/useCategorias'
import type { CategoriaTree } from '../../models/categoria'
import AplicarMargenForm from '../../components/productos/AplicarMargenForm'
import type { MargenFormValues } from '../../components/productos/AplicarMargenForm'
import AplicarMargenPreview from '../../components/productos/AplicarMargenPreview'
import type { PreviewItem } from '../../components/productos/AplicarMargenPreview'
import Toast, { useToast } from '../../components/ui/Toast'
import { aplicarMargenApi } from '../../api/productos'
import { ApiError } from '../../api/client'

function getDescendantIds(tree: CategoriaTree[], targetId: number): Set<number> {
  const result = new Set<number>()
  function collectAll(node: CategoriaTree) { result.add(node.id); node.subcategorias.forEach(collectAll) }
  function find(nodes: CategoriaTree[]): boolean {
    for (const node of nodes) { if (node.id === targetId) { collectAll(node); return true } if (find(node.subcategorias)) return true }
    return false
  }
  find(tree); return result
}

export default function AplicarMargenPage() {
  const qc = useQueryClient()
  const { data: prodData } = useQuery({
    queryKey: ['productos', 'margen-todos'],
    queryFn: () => getProductosApi(1, 1000, false),
  })
  const productos = prodData?.items ?? []
  const recargar = async () => { await qc.invalidateQueries({ queryKey: ['productos'] }) }
  const { tree }                = useCategorias()
  const { toasts, addToast, removeToast } = useToast()

  const [previewItems, setPreviewItems]     = useState<PreviewItem[]>([])
  const [previewSel, setPreviewSel]         = useState<Set<number>>(new Set())
  const [margenAplicado, setMargenAplicado] = useState(0)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [loadingAplicar, setLoadingAplicar] = useState(false)

  const handlePreview = (values: MargenFormValues) => {
    setLoadingPreview(true)
    try {
      let candidatos = productos.filter(p => p.tipo === 'MANUFACTURADO' && p.activo)
      if (values.modo === 'PRODUCTOS') {
        const ids = new Set(values.productoIdsSeleccionados)
        candidatos = candidatos.filter(p => ids.has(p.id))
      } else if (values.modo === 'CATEGORIA' && values.categoriaId) {
        const familiaIds = getDescendantIds(tree, values.categoriaId)
        candidatos = candidatos.filter(p => p.categorias.some(c => familiaIds.has(c.id)))
      }
      const items: PreviewItem[] = candidatos.map(p => ({
        id: p.id,
        nombre: p.nombre,
        precio_actual: p.precio_base,
        precio_costo: p.precio_costo,
        precio_nuevo: parseFloat((p.precio_costo * (1 + values.margen / 100)).toFixed(2)),
      }))
      setPreviewItems(items)
      setPreviewSel(new Set(items.map(i => i.id)))
      setMargenAplicado(values.margen)
    } finally {
      setLoadingPreview(false)
    }
  }

  const handleToggle = (id: number) => {
    setPreviewSel(prev => { const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next })
  }

  const handleToggleTodos = () => {
    if (previewSel.size === previewItems.length) setPreviewSel(new Set())
    else setPreviewSel(new Set(previewItems.map(i => i.id)))
  }

  const handleAplicar = async () => {
    const ids = [...previewSel]; if (ids.length === 0) return
    setLoadingAplicar(true)
    try {
      const res = await aplicarMargenApi({ scope: 'productos', producto_ids: ids, margen_porcentaje: margenAplicado })
      const cant = res.actualizados.length
      const ign  = res.ignorados.length
      addToast(
        `${cant} producto${cant !== 1 ? 's' : ''} actualizado${cant !== 1 ? 's' : ''}` +
        (ign > 0 ? `, ${ign} ignorado${ign !== 1 ? 's' : ''} (TERMINADO)` : '') + '. ✅',
        'success',
      )
      setPreviewItems([]); setPreviewSel(new Set()); await recargar()
    } catch (e) {
      addToast(e instanceof ApiError ? e.message : 'Error al aplicar el margen.', 'error')
    } finally {
      setLoadingAplicar(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Toast toasts={toasts} onRemove={removeToast} />
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">📊 Aplicar Margen Masivo</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Recalculá el precio de venta de múltiples productos aplicando un margen sobre su costo.
          Solo afecta a productos <strong>MANUFACTURADOS</strong>.
        </p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-6">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-4">Configuración</h2>
          <AplicarMargenForm onPreview={handlePreview} loading={loadingPreview} />
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-6">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-4">Vista previa</h2>
          {previewItems.length === 0 ? (
            <div className="py-12 text-center text-gray-400 dark:text-gray-500">
              <p className="text-3xl mb-2">📋</p>
              <p className="text-sm">Configurá los parámetros y presioná <strong>"Calcular preview"</strong> para ver los cambios antes de aplicarlos.</p>
            </div>
          ) : (
            <AplicarMargenPreview
              items={previewItems}
              seleccionados={previewSel}
              onToggle={handleToggle}
              onToggleTodos={handleToggleTodos}
              onAplicar={handleAplicar}
              loading={loadingAplicar}
            />
          )}
        </div>
      </div>
    </div>
  )
}