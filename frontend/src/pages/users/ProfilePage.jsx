import { useState } from 'react'

import useAuthStore from '../../store/authStore'
import { useHospital } from '../../api/assets'
import { useClientPortalSummary } from '../../api/clientPortal'
import PasswordStrength, { getStrength } from '../../components/ui/PasswordStrength'
import { RoleBadge } from './UsersPage'

const inputCls =
  'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30'

function Field({ label, children }) {
  return (
    <div>
      <p className="text-xs font-medium text-gray-500 mb-1">{label}</p>
      <div className="text-sm text-gray-800">{children}</div>
    </div>
  )
}

export default function ProfilePage() {
  const { user, changePassword } = useAuthStore()

  // /api/hospitals/<id>/ exige ADMIN o SUP, asi que a un CLI le devolvia 403 y
  // su propio hospital salia vacio. El resumen del portal si le pertenece.
  const isClient = user?.role === 'CLI'
  const { data: portal } = useClientPortalSummary({ enabled: isClient })
  const { data: adminHospital } = useHospital(
    !isClient && user?.hospital ? user.hospital : null
  )
  const hospitalName = isClient ? portal?.hospital?.name : adminHospital?.name

  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  if (!user) {
    return <p className="text-sm text-gray-500">Cargando perfil...</p>
  }

  function validate() {
    const errs = {}
    if (!current) errs.current = 'Ingresa tu contrasena actual.'
    if (next.length < 8) errs.next = 'Minimo 8 caracteres.'
    else if (getStrength(next) < 4)
      errs.next = 'Debe incluir mayuscula, numero y caracter especial.'
    if (next !== confirm) errs.confirm = 'Las contrasenas no coinciden.'
    return errs
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSuccess('')

    const errs = validate()
    if (Object.keys(errs).length) {
      setFieldErrors(errs)
      return
    }
    setFieldErrors({})
    setSaving(true)

    try {
      await changePassword(current, next, confirm)
      setCurrent('')
      setNext('')
      setConfirm('')
      setSuccess('Contrasena actualizada exitosamente')
    } catch (err) {
      const data = err?.response?.data
      if (data?.current_password) {
        setFieldErrors({ current: [].concat(data.current_password).join(' ') })
      } else if (data?.new_password) {
        setFieldErrors({ next: [].concat(data.new_password).join(' ') })
      } else if (data?.new_password_confirm) {
        setFieldErrors({ confirm: [].concat(data.new_password_confirm).join(' ') })
      } else {
        setError(data?.detail ?? 'No se pudo actualizar la contrasena.')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Mi perfil</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Para cambiar tu nombre, correo o rol contacta a un administrador.
        </p>
      </div>

      <section className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
        <h2 className="text-xs font-semibold text-gray-500 border-b border-gray-200 pb-2 mb-4">
          Datos de la cuenta
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Nombre completo">
            {user.full_name || `${user.first_name} ${user.last_name}`.trim()}
          </Field>
          <Field label="Email">{user.email}</Field>
          <Field label="Rol">
            <RoleBadge role={user.role} />
          </Field>
          {user.hospital && (
            <Field label="Hospital">{hospitalName ?? '—'}</Field>
          )}
          {user.role === 'TEC' && (
            <Field label="Codigo de empleado">{user.employee_code || '—'}</Field>
          )}
          {user.phone && <Field label="Telefono">{user.phone}</Field>}
        </div>
      </section>

      <section className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
        <h2 className="text-xs font-semibold text-gray-500 border-b border-gray-200 pb-2 mb-4">
          Cambiar contrasena
        </h2>

        {success && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-green-800 text-sm">
            {success}
          </div>
        )}
        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Contrasena actual
            </label>
            <input
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              disabled={saving}
              autoComplete="current-password"
              className={inputCls}
              placeholder="••••••••"
            />
            {fieldErrors.current && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.current}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nueva contrasena
            </label>
            <input
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              disabled={saving}
              autoComplete="new-password"
              className={inputCls}
              placeholder="••••••••"
            />
            {fieldErrors.next && <p className="mt-1 text-xs text-red-600">{fieldErrors.next}</p>}
            <PasswordStrength password={next} />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirmar nueva contrasena
            </label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              disabled={saving}
              autoComplete="new-password"
              className={inputCls}
              placeholder="••••••••"
            />
            {fieldErrors.confirm && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.confirm}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand/90 disabled:opacity-60 transition-colors"
          >
            {saving && (
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            )}
            {saving ? 'Actualizando...' : 'Actualizar contrasena'}
          </button>
        </form>
      </section>
    </div>
  )
}
