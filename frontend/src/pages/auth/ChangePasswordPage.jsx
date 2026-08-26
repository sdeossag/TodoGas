import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'

const ROLE_ROUTES = {
  ADMIN: '/dashboard',
  SUP: '/dashboard',
  TEC: '/mis-ordenes',
  CLI: '/mis-activos',
}

function getStrength(password) {
  let score = 0
  if (password.length >= 8) score++
  if (/[A-Z]/.test(password)) score++
  if (/\d/.test(password)) score++
  if (/[!@#$%^&*()\-_=+[\]{};:'",.<>/?\\|`~]/.test(password)) score++
  return score // 0-4
}

const STRENGTH_LABELS = ['', 'Débil', 'Regular', 'Buena', 'Fuerte']
const STRENGTH_COLORS = ['', 'bg-red-400', 'bg-yellow-400', 'bg-blue-400', 'bg-green-500']
const STRENGTH_TEXT = ['', 'text-red-600', 'text-yellow-600', 'text-blue-600', 'text-green-700']

export default function ChangePasswordPage() {
  const navigate = useNavigate()
  const { user, changePassword } = useAuthStore()

  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  const strength = getStrength(next)

  const validate = () => {
    const errs = {}
    if (!current) errs.current = 'Ingresa tu contraseña actual.'
    if (next.length < 8) errs.next = 'Mínimo 8 caracteres.'
    if (next !== confirm) errs.confirm = 'Las contraseñas no coinciden.'
    return errs
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const errs = validate()
    if (Object.keys(errs).length) {
      setFieldErrors(errs)
      return
    }
    setFieldErrors({})
    setIsLoading(true)

    try {
      await changePassword(current, next, confirm)
      const destination = ROLE_ROUTES[user?.role] ?? '/dashboard'
      navigate(destination, { replace: true })
    } catch (err) {
      const data = err.response?.data
      if (data?.current_password) {
        setFieldErrors((f) => ({ ...f, current: data.current_password.join(' ') }))
      } else if (data?.new_password) {
        setFieldErrors((f) => ({ ...f, next: data.new_password.join(' ') }))
      } else if (data?.detail) {
        setError(data.detail)
      } else {
        setError('No se pudo cambiar la contraseña. Intenta de nuevo.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-lg p-8">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-brand">Cambia tu contraseña</h1>
          <p className="text-sm text-gray-500 mt-1">
            Por seguridad debes establecer una contraseña nueva antes de continuar.
          </p>
        </div>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Contraseña actual */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Contraseña actual
            </label>
            <input
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              disabled={isLoading}
              className={`w-full px-3 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand
                ${fieldErrors.current ? 'border-red-400' : 'border-gray-300'}`}
              placeholder="••••••••"
            />
            {fieldErrors.current && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.current}</p>
            )}
          </div>

          {/* Nueva contraseña */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nueva contraseña
            </label>
            <input
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              disabled={isLoading}
              className={`w-full px-3 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand
                ${fieldErrors.next ? 'border-red-400' : 'border-gray-300'}`}
              placeholder="••••••••"
            />
            {fieldErrors.next && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.next}</p>
            )}

            {/* Indicador de fortaleza */}
            {next.length > 0 && (
              <div className="mt-2">
                <div className="flex gap-1 mb-1">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className={`h-1.5 flex-1 rounded-full transition-colors duration-300
                        ${strength >= i ? STRENGTH_COLORS[strength] : 'bg-gray-200'}`}
                    />
                  ))}
                </div>
                <p className={`text-xs font-medium ${STRENGTH_TEXT[strength] || 'text-gray-500'}`}>
                  {strength > 0 ? `Fortaleza: ${STRENGTH_LABELS[strength]}` : ''}
                </p>
                <ul className="mt-1 text-xs text-gray-500 space-y-0.5">
                  {next.length < 8 && <li>• Mínimo 8 caracteres</li>}
                  {!/[A-Z]/.test(next) && <li>• Al menos una mayúscula</li>}
                  {!/\d/.test(next) && <li>• Al menos un número</li>}
                  {!/[!@#$%^&*]/.test(next) && <li>• Al menos un carácter especial (!@#$%^&*)</li>}
                </ul>
              </div>
            )}
          </div>

          {/* Confirmar */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirmar nueva contraseña
            </label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              disabled={isLoading}
              className={`w-full px-3 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand
                ${fieldErrors.confirm ? 'border-red-400' : 'border-gray-300'}`}
              placeholder="••••••••"
            />
            {fieldErrors.confirm && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.confirm}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 px-4 bg-brand hover:bg-brand-light text-white
                       font-semibold rounded-lg text-sm transition-colors duration-150
                       focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand
                       disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading ? 'Guardando...' : 'Guardar nueva contraseña'}
          </button>
        </form>
      </div>
    </div>
  )
}
