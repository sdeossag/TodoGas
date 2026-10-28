import { useState } from 'react'
import { Link } from 'react-router-dom'
import { requestPasswordReset } from '../../api/auth'
import { validarCorreo } from '../../utils/restablecerContrasena'
import Icon from '../../components/ui/Icon'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [sent, setSent] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const errs = validarCorreo(email)
    if (Object.keys(errs).length) {
      setFieldErrors(errs)
      return
    }
    setFieldErrors({})
    setIsLoading(true)
    try {
      const data = await requestPasswordReset(email.trim().toLowerCase())
      setSent(
        data?.detail ||
          'Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña.',
      )
    } catch (err) {
      if (err.response?.status === 429) {
        setError('Hiciste demasiadas solicitudes. Intenta de nuevo en una hora.')
      } else {
        setError('Error de conexión. Verifica tu red e intenta de nuevo.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-dvh bg-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-lg p-8">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-brand">¿Olvidaste tu contraseña?</h1>
          <p className="text-sm text-gray-500 mt-1">
            Escribe tu correo y te enviaremos un enlace para elegir una contraseña nueva.
          </p>
        </div>

        {sent ? (
          <div
            role="status"
            className="mb-6 flex gap-3 px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-green-800 text-sm"
          >
            <Icon name="check" className="w-4 h-4 flex-shrink-0 mt-0.5 text-green-600" />
            <span>{sent}</span>
          </div>
        ) : (
          <>
            {error && (
              <div
                role="alert"
                className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm"
              >
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="email">
                  Correo electrónico
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  autoFocus
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    setFieldErrors({})
                  }}
                  disabled={isLoading}
                  aria-invalid={!!fieldErrors.email}
                  className={`w-full px-3 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand
                    ${fieldErrors.email ? 'border-red-400' : 'border-gray-300'}`}
                  placeholder="usuario@ejemplo.com"
                />
                {fieldErrors.email && (
                  <p className="mt-1 text-xs text-red-600">{fieldErrors.email}</p>
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
                {isLoading ? 'Enviando...' : 'Enviar enlace'}
              </button>
            </form>
          </>
        )}

        <p className="mt-6 text-sm text-center">
          <Link to="/login" className="text-brand hover:underline">
            Volver a iniciar sesión
          </Link>
        </p>
      </div>
    </div>
  )
}
