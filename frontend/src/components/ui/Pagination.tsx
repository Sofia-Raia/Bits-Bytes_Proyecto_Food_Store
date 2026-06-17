// src/components/ui/Pagination.tsx
interface PaginationProps {
  page: number
  totalPages: number
  total: number
  pageSize: number
  onPage: (n: number) => void
  loading?: boolean
}

export default function Pagination({ page, totalPages, total, pageSize, onPage, loading }: PaginationProps) {
  if (totalPages <= 1) return null

  const from = (page - 1) * pageSize + 1
  const to   = Math.min(page * pageSize, total)

  const pages: (number | '...')[] = []
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= page - 1 && i <= page + 1)) {
      pages.push(i)
    } else if (pages[pages.length - 1] !== '...') {
      pages.push('...')
    }
  }

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-1 pt-4">
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Mostrando <span className="font-medium text-gray-700 dark:text-gray-200">{from}–{to}</span> de{' '}
        <span className="font-medium text-gray-700 dark:text-gray-200">{total}</span> registro{total !== 1 ? 's' : ''}
      </p>

      <div className="flex items-center gap-1">
        <button
          onClick={() => onPage(page - 1)}
          disabled={page === 1 || loading}
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium
            text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          ← Anterior
        </button>

        {pages.map((p, i) =>
          p === '...' ? (
            <span key={`ellipsis-${i}`} className="px-2 py-1.5 text-sm text-gray-400 dark:text-gray-500">…</span>
          ) : (
            <button
              key={p}
              onClick={() => onPage(p as number)}
              disabled={loading}
              className={`w-9 h-9 rounded-lg text-sm font-medium transition
                ${p === page
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40'
                }`}
            >
              {p}
            </button>
          )
        )}

        <button
          onClick={() => onPage(page + 1)}
          disabled={page === totalPages || loading}
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium
            text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          Siguiente →
        </button>
      </div>
    </div>
  )
}
