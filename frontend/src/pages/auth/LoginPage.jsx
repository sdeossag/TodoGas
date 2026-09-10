import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import { SESSION_EXPIRED_KEY } from '../../api/client'
import Icon from '../../components/ui/Icon'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Un error del servidor tiene que poder leerse aunque el usuario empiece a
// reescribir de inmediato. Ver MODULO 3 de la auditoria.
const MIN_ERROR_MS = 3000

const ROLE_ROUTES = {
  ADMIN: '/dashboard',
  SUP: '/dashboard',
  TEC: '/mis-ordenes',
  CLI: '/mis-dashboard',
}

export default function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [showLogo, setShowLogo] = useState(true)
  const [showPassword, setShowPassword] = useState(false)

  // Instante en que se mostro el error actual, para no borrarlo antes de tiempo.
  const errorShownAt = useRef(0)
  const clearTimer = useRef(null)

  useEffect(() => {
    try {
      if (sessionStorage.getItem(SESSION_EXPIRED_KEY)) {
        sessionStorage.removeItem(SESSION_EXPIRED_KEY)
        setNotice('Tu sesión ha expirado. Vuelve a iniciar sesión.')
      }
    } catch {
      // sin sessionStorage no hay aviso que recuperar
    }
    return () => clearTimeout(clearTimer.current)
  }, [])

  function showError(message) {
    clearTimeout(clearTimer.current)
    errorShownAt.current = Date.now()
    setError(message)
  }

  /**
   * Retira el error al escribir, pero nunca antes de MIN_ERROR_MS: si no, el
   * aviso de "intentos restantes" desaparecia con la primera tecla.
   */
  function dismissError() {
    if (!error) return
    const elapsed = Date.now() - errorShownAt.current
    if (elapsed >= MIN_ERROR_MS) {
      setError('')
      return
    }
    clearTimeout(clearTimer.current)
    clearTimer.current = setTimeout(() => setError(''), MIN_ERROR_MS - elapsed)
  }

  function validate() {
    const errs = {}
    if (!email.trim()) errs.email = 'Ingresa tu correo electrónico.'
    else if (!EMAIL_RE.test(email.trim())) errs.email = 'El formato del correo no es válido.'
    if (!password) errs.password = 'Ingresa tu contraseña.'
    return errs
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setNotice('')

    const errs = validate()
    if (Object.keys(errs).length) {
      setFieldErrors(errs)
      return
    }
    setFieldErrors({})
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
        showError('Cuenta bloqueada temporalmente. Intenta de nuevo en 30 minutos.')
      } else if (status === 403) {
        showError('Tu cuenta está desactivada. Contacta al administrador.')
      } else if (detail) {
        showError(detail)
      } else {
        showError('Error de conexión. Verifica tu red e intenta de nuevo.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-dvh bg-gray-50 lg:grid lg:grid-cols-2">
      {/* ── Panel de marca ─────────────────────────────────────────────────
          Deliberadamente vacio: solo la marca sobre el navy. Quien entra aqui
          cada manana ya sabe que es la aplicacion, y una columna de texto que
          no se lee dos veces solo compite con el formulario. Su unico trabajo
          es dar composicion a la pagina y anclar la marca.
          Solo a partir de lg; en movil el formulario se queda con el sitio. */}
      <aside className="relative hidden lg:flex items-center justify-center overflow-hidden bg-brand-950 p-16 grain">
        {/* Dos focos de luz descentrados en vez de un degradado plano a 45
            grados, que es el fondo por defecto de cualquier plantilla. */}
        <div
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            backgroundImage:
              'radial-gradient(55rem 40rem at 30% 15%, rgba(64,112,176,0.26), transparent 62%),' +
              'radial-gradient(45rem 45rem at 85% 95%, rgba(30,58,95,0.55), transparent 65%)',
          }}
        />

        {showLogo ? (
          <img
            src="/logo-invertido-.png"
            alt="TodoGas"
            className="relative h-16 xl:h-20 w-auto"
            onError={() => setShowLogo(false)}
          />
        ) : (
          <p className="relative text-4xl font-semibold text-white tracking-tight">TodoGas</p>
        )}
      </aside>

      {/* ── Formulario ──────────────────────────────────────────────────── */}
      <main className="flex flex-col justify-center px-6 py-12 sm:px-10 lg:px-14 xl:px-20">
        <div className="w-full max-w-[26rem] mx-auto">
          {/* La marca en movil, donde el panel de la izquierda no existe. */}
          <div className="lg:hidden mb-10">
            {showLogo ? (
              <img
                src="/logo-mejorado-.png"
                alt="TodoGas CMMS"
                className="h-14 w-auto"
                onError={() => setShowLogo(false)}
              />
            ) : (
              <p className="text-2xl font-semibold text-brand tracking-tight">TodoGas CMMS</p>
            )}
          </div>

          <header className="mb-8">
            <h1 className="text-[1.75rem] font-semibold tracking-tightest text-gray-900 leading-tight">
              Entrar al sistema
            </h1>
            <p className="mt-2 text-sm text-gray-500">
              Usa las credenciales que te entregó el administrador de tu hospital.
            </p>
          </header>

          {/* Aviso de sesion expirada */}
          {notice && !error && (
            <div
              role="status"
              className="mb-6 flex gap-3 px-4 py-3 rounded-lg bg-amber-50 ring-1 ring-inset ring-amber-200 text-amber-900 text-sm animate-fade"
            >
              <Icon name="clock" className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-600" />
              <span>{notice}</span>
            </div>
          )}

          {/* Mensaje de error */}
          {error && (
            <div
              role="alert"
              className="mb-6 flex gap-3 px-4 py-3 rounded-lg bg-red-50 ring-1 ring-inset ring-red-200 text-red-800 text-sm animate-fade"
            >
              <Icon name="warning" className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-600" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5" htmlFor="email">
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
                  setFieldErrors((f) => ({ ...f, email: undefined }))
                  dismissError()
                }}
                onBlur={() => {
                  const value = email.trim()
                  if (value && !EMAIL_RE.test(value)) {
                    setFieldErrors((f) => ({ ...f, email: 'El formato del correo no es válido.' }))
                  }
                }}
                aria-invalid={!!fieldErrors.email}
                aria-describedby={fieldErrors.email ? 'email-error' : undefined}
                className={`input-field ${
                  fieldErrors.email ? 'border-red-400 focus:border-red-500 focus:ring-red-500/10' : ''
                }`}
                placeholder="usuario@ejemplo.com"
                disabled={isLoading}
              />
              {fieldErrors.email && (
                <p id="email-error" className="mt-1.5 text-xs text-red-600">
                  {fieldErrors.email}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5" htmlFor="password">
                Contraseña
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value)
                    setFieldErrors((f) => ({ ...f, password: undefined }))
                    dismissError()
                  }}
                  aria-invalid={!!fieldErrors.password}
                  aria-describedby={fieldErrors.password ? 'password-error' : undefined}
                  className={`input-field pr-11 ${
                    fieldErrors.password
                      ? 'border-red-400 focus:border-red-500 focus:ring-red-500/10'
                      : ''
                  }`}
                  placeholder="••••••••"
                  disabled={isLoading}
                />
                {/* Escribir una contrasena a ciegas en un movil, con guantes y
                    mala luz, es donde se pierden la mitad de los intentos. */}
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  aria-pressed={showPassword}
                  tabIndex={-1}
                  className="absolute inset-y-0 right-0 flex items-center px-3 text-gray-400 rounded-r-lg transition-colors hover:text-gray-600 focus-visible:outline-none focus-visible:text-brand-600"
                >
                  <Icon name={showPassword ? 'eyeOff' : 'eye'} className="w-[18px] h-[18px]" />
                </button>
              </div>
              {fieldErrors.password && (
                <p id="password-error" className="mt-1.5 text-xs text-red-600">
                  {fieldErrors.password}
                </p>
              )}
            </div>

            <button type="submit" disabled={isLoading} className="btn-primary w-full py-3">
              {isLoading && (
                <svg
                  className="animate-spin h-4 w-4 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
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

          <p className="mt-8 text-xs leading-relaxed text-gray-500">
            ¿No puedes entrar? El administrador de tu organización puede restablecer tu
            contraseña desde el módulo de usuarios.
          </p>
        </div>
      </main>
    </div>
  )
}
