// src/components/ui/Skeleton.tsx

/** Fila de tabla con celdas pulsantes. `cols` = cantidad de columnas. */
export function SkeletonRow({ cols }: { cols: number }) {
  const widths = ['w-20', 'w-36', 'w-48', 'w-24', 'w-16', 'w-28']
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-5 py-4">
          <div className={`h-4 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse ${widths[i % widths.length]}`} />
        </td>
      ))}
    </tr>
  )
}

/** Card de producto pulsante para la grilla. */
export function SkeletonCard() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 overflow-hidden">
      <div className="w-full h-40 bg-gray-200 dark:bg-gray-700 animate-pulse" />
      <div className="p-4 flex flex-col gap-3">
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-16" />
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-3/4" />
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-1/2" />
        <div className="flex gap-2 mt-2">
          <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse w-16" />
          <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse w-20" />
        </div>
      </div>
    </div>
  )
}
