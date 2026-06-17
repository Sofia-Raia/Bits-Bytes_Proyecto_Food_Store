// src/components/categorias/CategoriaTreeNode.tsx
import type { CategoriaTree } from '../../models/categoria'
import { useState } from 'react'

interface Props { node: CategoriaTree; depth?: number; isAdmin: boolean; onEdit: (c: CategoriaTree) => void; onDesactivar: (c: CategoriaTree) => void; onReactivar: (c: CategoriaTree) => void; onAddChild: (parent: CategoriaTree) => void }

export default function CategoriaTreeNode({ node, depth = 0, isAdmin, onEdit, onDesactivar, onReactivar, onAddChild }: Props) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = node.subcategorias.length > 0

  return (
    <div>
      <div
        className={`flex items-center gap-2 py-2.5 px-3 rounded-xl transition group ${!node.activo ? 'opacity-50' : 'hover:bg-gray-50 dark:hover:bg-gray-700/40'}`}
        style={{ paddingLeft: `${12 + depth * 24}px` }}
      >
        <button onClick={() => setExpanded(p => !p)} className={`w-5 h-5 flex items-center justify-center text-gray-400 dark:text-gray-500 transition ${!hasChildren ? 'invisible' : ''}`}>
          {expanded ? '▾' : '▸'}
        </button>
        <span className="text-base">{depth === 0 ? '📁' : '📄'}</span>
        <span className="font-mono text-xs bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 px-1.5 py-0.5 rounded font-semibold">{node.codigo}</span>
        <span className={`text-sm font-medium flex-1 ${!node.activo ? 'text-gray-400 dark:text-gray-500 line-through' : 'text-gray-800 dark:text-gray-200'}`}>{node.nombre}</span>
        {!node.activo && <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/40 text-red-500 dark:text-red-300">Inactivo</span>}
        {hasChildren && node.activo && <span className="text-xs text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">{node.subcategorias.filter(s => s.activo).length}</span>}
        {isAdmin && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
            {node.activo ? (
              <>
                <button onClick={() => onAddChild(node)} className="text-xs text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/30 px-2 py-1 rounded-lg transition">+ Sub</button>
                <button onClick={() => onEdit(node)} className="text-xs text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 px-2 py-1 rounded-lg transition">Editar</button>
                <button onClick={() => onDesactivar(node)} className="text-xs text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 px-2 py-1 rounded-lg transition">Desactivar</button>
              </>
            ) : (
              <button onClick={() => onReactivar(node)} className="text-xs text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/30 px-2 py-1 rounded-lg transition">Reactivar</button>
            )}
          </div>
        )}
      </div>
      {expanded && hasChildren && (
        <div className="border-l-2 border-gray-100 dark:border-gray-700 ml-6">
          {node.subcategorias.map(child => (
            <CategoriaTreeNode key={child.id} node={child} depth={depth + 1} isAdmin={isAdmin} onEdit={onEdit} onDesactivar={onDesactivar} onReactivar={onReactivar} onAddChild={onAddChild} />
          ))}
        </div>
      )}
    </div>
  )
}
