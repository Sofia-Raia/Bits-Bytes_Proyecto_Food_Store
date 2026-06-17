// src/pages/NotFoundPage.tsx
import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center px-4 text-center">
      <div className="mb-6 select-none">
        <span className="text-8xl">🍽️</span>
      </div>
      <h1 className="text-6xl font-extrabold text-gray-800 dark:text-gray-100 mb-2">404</h1>
      <p className="text-xl font-semibold text-gray-600 dark:text-gray-300 mb-1">Página no encontrada</p>
      <p className="text-sm text-gray-400 dark:text-gray-500 mb-8 max-w-xs">
        La ruta que buscás no existe. Quizás fue movida o escribiste mal la URL.
      </p>
      <Link
        to="/pedidos"
        className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-xl transition text-sm"
      >
        ← Volver al inicio
      </Link>
    </div>
  )
}
