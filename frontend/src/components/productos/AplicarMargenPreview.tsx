// src/components/productos/AplicarMargenPreview.tsx
export interface PreviewItem { id: number; nombre: string; precio_actual: number; precio_costo: number; precio_nuevo: number }
interface Props { items: PreviewItem[]; seleccionados: Set<number>; onToggle: (id: number) => void; onToggleTodos: () => void; onAplicar: () => void; loading: boolean }

export default function AplicarMargenPreview({ items, seleccionados, onToggle, onToggleTodos, onAplicar, loading }: Props) {
  if (items.length === 0) return null
  const todosSeleccionados = seleccionados.size === items.length

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">
          Preview de cambios <span className="ml-1.5 text-xs text-gray-400 dark:text-gray-500 font-normal">({seleccionados.size} de {items.length} seleccionados)</span>
        </h3>
        <button type="button" onClick={onToggleTodos} className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 font-medium">
          {todosSeleccionados ? 'Deseleccionar todos' : 'Seleccionar todos'}
        </button>
      </div>

      <div className="border border-gray-200 dark:border-gray-600 rounded-xl overflow-hidden">
        <div className="overflow-x-auto max-h-72 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700/50 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-2.5 text-left w-10"><input type="checkbox" checked={todosSeleccionados} onChange={onToggleTodos} className="w-4 h-4 accent-blue-600" /></th>
                <th className="px-3 py-2.5 text-left font-semibold text-gray-600 dark:text-gray-300">Producto</th>
                <th className="px-3 py-2.5 text-right font-semibold text-gray-600 dark:text-gray-300">Precio actual</th>
                <th className="px-3 py-2.5 text-right font-semibold text-gray-600 dark:text-gray-300">Precio costo</th>
                <th className="px-3 py-2.5 text-right font-semibold text-gray-600 dark:text-gray-300">Precio nuevo</th>
                <th className="px-3 py-2.5 text-right font-semibold text-gray-600 dark:text-gray-300">Δ</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
              {items.map(item => {
                const delta = item.precio_nuevo - item.precio_actual
                const isChecked = seleccionados.has(item.id)
                return (
                  <tr key={item.id}
                    className={`transition cursor-pointer ${isChecked ? 'bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30' : 'hover:bg-gray-50 dark:hover:bg-gray-700/40 opacity-50'}`}
                    onClick={() => onToggle(item.id)}>
                    <td className="px-4 py-2.5"><input type="checkbox" checked={isChecked} onChange={() => onToggle(item.id)} onClick={e => e.stopPropagation()} className="w-4 h-4 accent-blue-600" /></td>
                    <td className="px-3 py-2.5 font-medium text-gray-800 dark:text-gray-200">{item.nombre}</td>
                    <td className="px-3 py-2.5 text-right text-gray-600 dark:text-gray-400">${item.precio_actual.toFixed(2)}</td>
                    <td className="px-3 py-2.5 text-right text-gray-500 dark:text-gray-500">${item.precio_costo.toFixed(2)}</td>
                    <td className="px-3 py-2.5 text-right font-bold text-gray-800 dark:text-gray-200">${item.precio_nuevo.toFixed(2)}</td>
                    <td className={`px-3 py-2.5 text-right text-xs font-semibold ${delta >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      {delta >= 0 ? '+' : ''}{delta.toFixed(2)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      <button type="button" onClick={onAplicar} disabled={seleccionados.size === 0 || loading}
        className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl text-sm font-semibold text-white transition">
        {loading ? 'Aplicando...' : `✅ Aplicar a ${seleccionados.size} producto${seleccionados.size !== 1 ? 's' : ''}`}
      </button>
    </div>
  )
}
