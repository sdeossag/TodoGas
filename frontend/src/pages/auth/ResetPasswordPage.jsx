import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { confirmPasswordReset } from '../../api/auth'
import { validarNuevaContrasena } from '../../utils/restablecerContrasena'
import PasswordStrength from '../../components/ui/PasswordStrength'

const DONE_NOTICE = 'Contraseña actualizada. Ya puedes iniciar sesión.'

export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const uid = params.get('uid') || ''
  const token = params.get('token') || ''

  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  const linkIncomplete = !uid || !token

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const errs = validarNuevaContrasena(next, confirm)
    if (Object.keys(errs).length) {
      setFieldErrors(errs)
      return
    }
    setFieldErrors({})
    setIsLoading(true)
    try {
      await confirmPasswordReset({ uid, token, newPassword: next })
      navigate('/login', { replace: true, state: { notice: DONE_NOTICE } })
    } catch (err) {
      const data = err.response?.data
      if (data?.new_password) {
        setFieldErrors((f) => ({ ...f, next: [].concat(data.new_password).join(' ') }))
      } else if (data?.detail) {
        setError(data.detail)
      } else if (err.response?.status === 429) {
        setError('Demasiados intentos. Intenta de nuevo más tarde.')
      } else if (err.response) {
        setError('El enlace no es válido o ya venció. Solicita uno nuevo.')
      } else {
        setError('Error de conexión. Verifica tu red e intenta de nuevo.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const needsNewLink = linkIncomplete || !!error

  return (
    <div className="min-h-dvh bg-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-lg p-8">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-brand">Elige tu nueva contraseña</h1>
          <p className="text-sm text-gray-500 mt-1">
            Usa mínimo 8 caracteres, con una mayúscula, un número y un símbolo.
          </p>
        </div>

        {linkIncomplete ? (
          <div
            role="alert"
            className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm"
          >
            El enlace está incompleto. Solicita uno nuevo.
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
                <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="new-password">
                  Nueva contraseña
                </label>
                <input
                  id="new-password"
                  type="password"
                  autoComplete="new-password"
                  autoFocus
                  value={next}
                  onChange={(e) => setNext(e.target.value)}
                  disabled={isLoading}
                  className={`w-full px-3 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand
                    ${fieldErrors.next ? 'border-red-400' : 'border-gray-300'}`}
                  placeholder="••••••••"
                />
                {fieldErrors.next && <p className="mt-1 text-xs text-red-600">{fieldErrors.next}</p>}
                <PasswordStrength password={next} />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="confirm-password">
                  Confirmar nueva contraseña
                </label>
                <input
                  id="confirm-password"
                  type="password"
                  autoComplete="new-password"
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
          </>
        )}

        <p className="mt-6 text-sm text-center">
          <Link
            to={needsNewLink ? '/olvide-contrasena' : '/login'}
            className="text-brand hover:underline"
          >
            {needsNewLink ? 'Solicitar un enlace nuevo' : 'Volver a iniciar sesión'}
          </Link>
        </p>
      </div>
    </div>
  )
}
