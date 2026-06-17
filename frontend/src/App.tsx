// src/App.tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import PrivateRoute from './routes/PrivateRoute'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import IngredientesPage from './pages/ingredientes/IngredientesPage'
import CategoriasPage from './pages/categorias/CategoriasPage'
import ProductosPage from './pages/productos/ProductosPage'
import AplicarMargenPage from './pages/productos/AplicarMargenPage'
import UsuariosPage from './pages/usuarios/UsuariosPage'
import PedidosPage from './pages/pedidos/PedidosPage'
import PedidoDetallePage from './pages/pedidos/PedidoDetallePage'
import PagoResultadoPage from './pages/pedidos/PagoResultadoPage'
import DireccionesPage from './pages/direcciones/DireccionesPage'
import NotFoundPage from './pages/NotFoundPage'
import StorePage      from './pages/store/StorePage'
import CarritoPage    from './pages/store/CarritoPage'
import CheckoutPage   from './pages/store/CheckoutPage'
import MisPedidosPage from './pages/store/MisPedidosPage'
import EstadisticasPage from './pages/estadisticas/EstadisticasPage'

function AppRoutes() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <Navbar />
      <Routes>
        {/* Redirigir raíz a tienda */}
        <Route path="/" element={<Navigate to="/store" replace />} />
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* ── Pedidos — todos los roles autenticados (CLIENT ve los suyos) ── */}
        <Route
          path="/pedidos"
          element={
            <PrivateRoute>
              <PedidosPage />
            </PrivateRoute>
          }
        />

        {/* ── Detalle de pedido — todos los roles autenticados ── */}
        <Route
          path="/pedidos/:id"
          element={
            <PrivateRoute>
              <PedidoDetallePage />
            </PrivateRoute>
          }
        />

        {/* ── Resultado del pago MercadoPago (redirect back_urls) ── */}
        <Route
          path="/pedidos/:id/pago/:status"
          element={
            <PrivateRoute>
              <PagoResultadoPage />
            </PrivateRoute>
          }
        />

        {/* ── Ingredientes — ADMIN, STOCK ── */}
        <Route
          path="/ingredientes"
          element={
            <PrivateRoute roles={['ADMIN', 'STOCK']}>
              <IngredientesPage />
            </PrivateRoute>
          }
        />

        {/* ── Categorías — ADMIN, STOCK ── */}
        <Route
          path="/categorias"
          element={
            <PrivateRoute roles={['ADMIN', 'STOCK']}>
              <CategoriasPage />
            </PrivateRoute>
          }
        />

        {/* ── Productos — ADMIN, STOCK ── */}
        <Route
          path="/productos"
          element={
            <PrivateRoute roles={['ADMIN', 'STOCK']}>
              <ProductosPage />
            </PrivateRoute>
          }
        />

        {/* ── Margen masivo — ADMIN, STOCK ── */}
        <Route
          path="/productos/aplicar-margen"
          element={
            <PrivateRoute roles={['ADMIN', 'STOCK']}>
              <AplicarMargenPage />
            </PrivateRoute>
          }
        />

        {/* ── Estadísticas — solo ADMIN ── */}
        <Route
          path="/estadisticas"
          element={
            <PrivateRoute roles={['ADMIN']}>
              <EstadisticasPage />
            </PrivateRoute>
          }
        />

        {/* ── Usuarios — solo ADMIN ── */}
        <Route
          path="/usuarios"
          element={
            <PrivateRoute roles={['ADMIN']}>
              <UsuariosPage />
            </PrivateRoute>
          }
        />

        {/* ── Direcciones — todos los roles autenticados ── */}
        <Route
          path="/direcciones"
          element={
            <PrivateRoute>
              <DireccionesPage />
            </PrivateRoute>
          }
        />

        {/* ── Tienda pública ── */}
        <Route path="/store"         element={<StorePage />} />
        <Route path="/store/carrito" element={<CarritoPage />} />

        {/* ── Tienda protegida ── */}
        <Route path="/store/checkout" element={
          <PrivateRoute><CheckoutPage /></PrivateRoute>
        } />
        <Route path="/store/mis-pedidos" element={
          <PrivateRoute><MisPedidosPage /></PrivateRoute>
        } />

        <Route
          path="*"
          element={
            <PrivateRoute>
              <NotFoundPage />
            </PrivateRoute>
          }
        />
      </Routes>
    </div>
  )
}

export default function App() {
  return <AppRoutes />
}
