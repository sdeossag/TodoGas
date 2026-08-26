import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'

const ROLE_ROUTES = {
  ADMIN: '/dashboard',
  SUP: '/dashboard',
  TEC: '/mis-ordenes',
  CLI: '/mis-activos',
}

export default function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [showLogo, setShowLogo] = useState(true)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const user = await login(email, password)

      if (user.must_change_password) {
        navigate('/cambiar-contrasena', { replace: true })
        return
      }

      const destination = ROLE_ROUTES[user.role] ?? '/dashboard'
      navigate(destination, { replace: true })
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail

      if (status === 429) {
        setError('Cuenta bloqueada temporalmente. Intenta de nuevo en 30 minutos.')
      } else if (status === 403) {
        setError('Tu cuenta está desactivada. Contacta al administrador.')
      } else if (detail) {
        setError(detail)
      } else {
        setError('Error de conexión. Verifica tu red e intenta de nuevo.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-lg p-8">
        {/* Logo / Marca */}
        <div className="flex flex-col items-center text-center mb-8">
          {showLogo ? (
            <img
              src="/logo-mejorado-.png"
              alt="TodoGas CMMS"
              className="h-20 w-auto mx-auto mb-5"
              onError={() => setShowLogo(false)}
            />
          ) : (
            <p className="text-2xl font-bold text-brand tracking-tight mb-2">TodoGas CMMS</p>
          )}
          <h1 className="text-base font-semibold text-gray-700">
            Sistema de gestión de mantenimiento
          </h1>
        </div>

        {/* Mensaje de error */}
        {error && (
          <div className="mb-5 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="email">
              Correo electrónico
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => { setEmail(e.target.value); setError('') }}
              className="input-field"
              placeholder="usuario@ejemplo.com"
              disabled={isLoading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="password">
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError('') }}
              className="input-field"
              placeholder="••••••••"
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="btn-primary w-full py-2.5"
          >
            {isLoading && (
              <svg
                className="animate-spin h-4 w-4 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v8H4z"
                />
              </svg>
            )}
            {isLoading ? 'Iniciando sesión...' : 'Iniciar sesión'}
          </button>
        </form>
      </div>
    </div>
  )
}
