// src/components/ui/Toast.tsx
import { useEffect } from 'react'
import { useUiStore } from '../../store/uiStore'
import type { ToastType, ToastData } from '../../store/uiStore'

// Se re-exportan los tipos desde el store para no romper imports existentes.
export type { ToastType, ToastData }

interface Props {
  toasts: ToastData[]
  onRemove: (id: number) => void
}

const icons: Record<ToastType, string> = {
  success: '✓',
  error:   '✕',
  info:    'ℹ',
}

const colors: Record<ToastType, string> = {
  success: 'bg-green-600',
  error:   'bg-red-600',
  info:    'bg-blue-600',
}

function ToastItem({ toast, onRemove }: { toast: ToastData; onRemove: (id: number) => void }) {
  useEffect(() => {
    const t = setTimeout(() => onRemove(toast.id), 3500)
    return () => clearTimeout(t)
  }, [toast.id, onRemove])

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-white text-sm font-medium ${colors[toast.type]}`}
    >
      <span className="font-bold text-base">{icons[toast.type]}</span>
      <span className="flex-1">{toast.message}</span>
      <button
        onClick={() => onRemove(toast.id)}
        className="ml-2 opacity-70 hover:opacity-100 transition"
      >
        ✕
      </button>
    </div>
  )
}

export default function Toast({ toasts, onRemove }: Props) {
  if (!toasts.length) return null
  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map(t => (
        <ToastItem key={t.id} toast={t} onRemove={onRemove} />
      ))}
    </div>
  )
}

/**
 * Hook de toasts respaldado por el uiStore global.
 *
 * Conserva la firma del hook original (`toasts`, `addToast`, `removeToast`) para
 * que las páginas no cambien su uso; la cola de toasts ahora es global, así que
 * cualquier página que monte un `<Toast />` refleja el mismo estado.
 */
export function useToast() {
  const toasts = useUiStore(s => s.toasts)
  const addToast = useUiStore(s => s.addToast)
  const removeToast = useUiStore(s => s.removeToast)
  return { toasts, addToast, removeToast }
}
