// src/pages/auth/RegisterPage.tsx
import { useState } from 'react'
import { Link, useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../../store/authStore'
import type { RegisterData } from '../../api/auth'

interface FormState {
  nombre: string
  apellido: string
  email: string
  password: string
  confirmar: string
}

function validate(form: FormState): string | null {
  if (form.nombre.trim().length < 2)    return 'El nombre debe tener al menos 2 caracteres.'
  if (form.apellido.trim().length < 2)  return 'El apellido debe tener al menos 2 caracteres.'
  const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRe.test(form.email))        return 'El email no tiene un formato válido.'
  if (form.password.length < 8)         return 'La contraseña debe tener al menos 8 caracteres.'
  if (form.password !== form.confirmar) return 'Las contraseñas no coinciden.'
  return null
}

export default function RegisterPage() {
  const { register, user } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState<FormState>({
    nombre: '', apellido: '', email: '', password: '', confirmar: '',
  })
  const [error,   setError]   = useState('')
  const [loading, setLoading] = useState(false)

  if (user) return <Navigate to="/pedidos" replace />

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    const validationError = validate(form)
    if (validationError) { setError(validationError); return }
    setLoading(true)
    try {
      const data: RegisterData = {
        nombre:   form.nombre.trim(),
        apellido: form.apellido.trim(),
        email:    form.email.trim(),
        password: form.password,
      }
      await register(data)
      navigate('/pedidos')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al registrarse'
      if (msg.includes('ya está registrado') || msg.includes('409')) {
        setError('Este email ya está registrado. ¿Querés iniciar sesión?')
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  const field = (
    name: keyof FormState,
    label: string,
    type = 'text',
    autocomplete = 'off'
  ) => (
    <div className="flex flex-col gap-1">
      <label htmlFor={name} className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
        {label}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        value={form[name]}
        onChange={handleChange}
        required
        autoComplete={autocomplete}
        className="border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400 text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 text-sm placeholder-gray-400 dark:placeholder-gray-500"
      />
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-950 flex flex-col items-center justify-center px-4 py-10">
      <div className="text-center mb-6">
        <p className="text-5xl mb-3">🍴</p>
        <h1 className="text-3xl font-bold text-blue-700 dark:text-blue-400">Food Store</h1>
        <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Crear cuenta</p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-md w-full max-w-sm p-8 flex flex-col gap-4"
      >
        {field('nombre',   'Nombre',   'text', 'given-name')}
        {field('apellido', 'Apellido', 'text', 'family-name')}
        {field('email',    'Email',    'email', 'email')}
        {field('password', 'Contraseña',          'password', 'new-password')}
        {field('confirmar', 'Confirmar contraseña', 'password', 'new-password')}

        {error && (
          <p className="text-sm text-red-500 text-center bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-xl transition disabled:opacity-50"
        >
          {loading ? 'Registrando...' : 'Crear cuenta'}
        </button>

        <p className="text-sm text-center text-gray-500 dark:text-gray-400">
          ¿Ya tenés cuenta?{' '}
          <Link to="/login" className="text-blue-600 dark:text-blue-400 hover:underline font-medium">
            Iniciá sesión
          </Link>
        </p>
      </form>
    </div>
  )
}
