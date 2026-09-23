import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  useCreateUser,
  useDeactivateUser,
  useResetPassword,
  useUpdateUser,
  useUsers,
} from '../../api/users'
import { useAssetNodes, useHospitals } from '../../api/assets'
import { useAuditLog } from '../../api/audit'
import useAuthStore from '../../store/authStore'
import Icon from '../../components/ui/Icon'
import { entityTypeLabel } from '../../constants/labels'
import useModalDismiss from '../../hooks/useModalDismiss'

export const ROLE_LABELS = {
  ADMIN: 'Administrador',
  SUP: 'Supervisor',
  TEC: 'Tecnico',
  CLI: 'Cliente',
}

export const ROLE_BADGE = {
  ADMIN: 'bg-red-100 text-red-800',
  SUP: 'bg-purple-100 text-purple-800',
  TEC: 'bg-blue-100 text-blue-800',
  CLI: 'bg-green-100 text-green-800',
}

const ACTION_LABELS = {
  CREATE: 'Creo',
  UPDATE: 'Actualizo',
  DELETE: 'Elimino',
  STATUS_CHANGE: 'Cambio estado',
  LOGIN: 'Inicio sesion',
  SYNC: 'Sincronizo',
}

const SPECIAL = '!@#$%^&*'
const NOTICE_MS = 5000

/**
 * Contrasena temporal generada en el cliente.
 *
 * POST /api/users/ exige el campo `password`: el backend no la inventa, solo
 * la reenvia por correo y marca must_change_password. Se construye para
 * satisfacer StrongPasswordValidator sin depender del azar.
 */
function generateTempPassword() {
  const upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
  const lower = 'abcdefghijkmnopqrstuvwxyz'
  const digits = '23456789'
  const pick = (set) => set[Math.floor(Math.random() * set.length)]

  const chars = [pick(upper), pick(lower), pick(digits), pick(SPECIAL)]
  const all = upper + lower + digits + SPECIAL
  while (chars.length < 14) chars.push(pick(all))

  // Fisher-Yates: si no, los cuatro obligatorios quedan siempre al principio.
  for (let i = chars.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[chars[i], chars[j]] = [chars[j], chars[i]]
  }
  return chars.join('')
}

function fieldError(err, field) {
  const data = err?.response?.data
  if (!data || typeof data === 'string') return null
  const val = data[field]
  if (!val) return null
  return Array.isArray(val) ? val.join(' ') : String(val)
}

function generalError(err, fallback) {
  const data = err?.response?.data
  if (!data) return err?.message || fallback
  if (typeof data === 'string') return data
  if (data.detail) return String(data.detail)
  const firstKey = Object.keys(data)[0]
  if (!firstKey) return fallback
  const val = data[firstKey]
  return Array.isArray(val) ? `${firstKey}: ${val[0]}` : `${firstKey}: ${val}`
}

function formatDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-CO', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function Spinner({ className = 'h-4 w-4' }) {
  return (
    <svg className={`animate-spin ${className}`} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

export function RoleBadge({ role }) {
  return (
    <span
      className={`inline-flex px-2 py-0.5 text-xs rounded-full font-medium ${
        ROLE_BADGE[role] ?? 'bg-gray-100 text-gray-700'
      }`}
    >
      {ROLE_LABELS[role] ?? role}
    </span>
  )
}

function StatusCell({ active }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-gray-600">
      <span
        className={`h-2 w-2 rounded-full ${active ? 'bg-green-500' : 'bg-gray-400'}`}
        aria-hidden="true"
      />
      {active ? 'Activo' : 'Inactivo'}
    </span>
  )
}

function Modal({ title, onClose, children, wide = false }) {
  useModalDismiss(onClose)

  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-gray-900/40 p-4 sm:p-6">
      <div
        className={`w-full ${wide ? 'max-w-2xl' : 'max-w-lg'} my-8 bg-white rounded-xl shadow-xl`}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-800">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="p-1 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <Icon name="close" className="w-5 h-5" />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  )
}

const inputCls =
  'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30'
const labelCls = 'block text-xs font-medium text-gray-500 mb-1'

// ── Confirmacion inline ──────────────────────────────────────────────────────

function InlineConfirm({ message, confirmLabel, onConfirm, onCancel, pending, danger }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2">
      <p className="flex-1 text-xs text-amber-900">{message}</p>
      <button
        type="button"
        onClick={onConfirm}
        disabled={pending}
        className={`px-2.5 py-1 text-xs font-medium rounded text-white disabled:opacity-60 ${
          danger ? 'bg-red-600 hover:bg-red-700' : 'bg-brand hover:bg-brand/90'
        }`}
      >
        {pending ? '...' : confirmLabel}
      </button>
      <button
        type="button"
        onClick={onCancel}
        disabled={pending}
        className="px-2.5 py-1 text-xs text-gray-600 rounded border border-gray-200 hover:bg-white disabled:opacity-60"
      >
        Cancelar
      </button>
    </div>
  )
}

// ── Modal de creacion (PASO 3) ───────────────────────────────────────────────

function CreateUserModal({ hospitals, onClose, onCreated }) {
  const create = useCreateUser()
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    role: 'TEC',
    hospital: '',
    scope_node: '',
    employee_code: '',
    phone: '',
  })
  const [errors, setErrors] = useState({})
  const [apiError, setApiError] = useState('')

  const set = (k) => (e) => {
    setForm((f) => ({ ...f, [k]: e.target.value }))
    setErrors((prev) => (prev[k] ? { ...prev, [k]: undefined } : prev))
  }

  function validate() {
    const errs = {}
    if (!form.first_name.trim()) errs.first_name = 'El nombre es requerido.'
    if (!form.last_name.trim()) errs.last_name = 'El apellido es requerido.'
    if (!form.email.trim()) errs.email = 'El email es requerido.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim()))
      errs.email = 'El formato del email no es valido.'
    if (form.role === 'CLI' && !form.hospital) errs.hospital = 'El hospital es requerido para clientes.'
    return errs
  }

  function handleSubmit(e) {
    e.preventDefault()
    setApiError('')
    const errs = validate()
    if (Object.keys(errs).length) {
      setErrors(errs)
      return
    }

    const payload = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim().toLowerCase(),
      role: form.role,
      employee_code: form.role === 'TEC' ? form.employee_code.trim() : '',
      phone: form.role === 'TEC' ? form.phone.trim() : '',
      hospital: form.role !== 'ADMIN' ? form.hospital || null : null,
      scope_node: form.role !== 'ADMIN' ? form.scope_node || null : null,
      password: generateTempPassword(),
    }

    create.mutate(payload, {
      onSuccess: () => onCreated(payload.email),
      onError: (err) => {
        const emailErr = fieldError(err, 'email')
        if (emailErr) {
          setErrors((prev) => ({ ...prev, email: emailErr }))
          return
        }
        const alcanceErr = fieldError(err, 'hospital') || fieldError(err, 'scope_node')
        if (alcanceErr) {
          setErrors((prev) => ({ ...prev, hospital: alcanceErr }))
          return
        }
        const passwordErr = fieldError(err, 'password')
        if (passwordErr) {
          // La temporal la genera el front: si el validador la rechaza es un
          // bug nuestro, no algo que el admin pueda corregir en el formulario.
          setApiError(`La contrasena temporal generada fue rechazada: ${passwordErr}`)
          return
        }
        setApiError(generalError(err, 'No se pudo crear el usuario.'))
      },
    })
  }

  return (
    <Modal title="Nuevo usuario" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className={labelCls}>
              Nombre <span className="text-red-400">*</span>
            </label>
            <input type="text" value={form.first_name} onChange={set('first_name')} className={inputCls} />
            {errors.first_name && <p className="mt-1 text-xs text-red-600">{errors.first_name}</p>}
          </div>
          <div>
            <label className={labelCls}>
              Apellido <span className="text-red-400">*</span>
            </label>
            <input type="text" value={form.last_name} onChange={set('last_name')} className={inputCls} />
            {errors.last_name && <p className="mt-1 text-xs text-red-600">{errors.last_name}</p>}
          </div>
        </div>

        <div>
          <label className={labelCls}>
            Email <span className="text-red-400">*</span>
          </label>
          <input type="email" value={form.email} onChange={set('email')} className={inputCls} />
          {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email}</p>}
        </div>

        <div>
          <label className={labelCls}>
            Rol <span className="text-red-400">*</span>
          </label>
          <select value={form.role} onChange={set('role')} className={inputCls}>
            {Object.entries(ROLE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </div>

        <AlcanceFields
          role={form.role}
          hospitals={hospitals}
          hospital={form.hospital}
          scopeNode={form.scope_node}
          error={errors.hospital}
          onChange={(cambios) => {
            setForm((f) => ({ ...f, ...cambios }))
            setErrors((prev) => ({ ...prev, hospital: undefined }))
          }}
        />

        {form.role === 'TEC' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Codigo de empleado</label>
              <input
                type="text"
                value={form.employee_code}
                onChange={set('employee_code')}
                placeholder="Cedula"
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Telefono</label>
              <input type="text" value={form.phone} onChange={set('phone')} className={inputCls} />
            </div>
          </div>
        )}

        <p className="text-xs text-gray-500">
          Se generara una contrasena temporal y se enviara al correo del usuario, que debera
          cambiarla en su primer inicio de sesion.
        </p>

        {apiError && <p className="text-sm text-red-600">{apiError}</p>}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            disabled={create.isPending}
            className="px-4 py-2 border border-gray-200 text-gray-600 text-sm rounded-lg hover:bg-gray-50 disabled:opacity-60"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={create.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand/90 disabled:opacity-60"
          >
            {create.isPending && <Spinner />}
            {create.isPending ? 'Creando...' : 'Crear usuario'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

// ── Alcance: hospital y parte del arbol ──────────────────────────────────────

/**
 * A qué se limita el usuario (apps/users/scope.py): un hospital y, dentro,
 * una parte del árbol, como "Limitar acceso a esta localización" de Fracttal.
 * La cuenta de hospital siempre tiene uno; al resto es opcional, y el
 * administrador nunca se limita (el servidor lo ignora).
 */
function AlcanceFields({ role, hospitals, hospital, scopeNode, onChange, error }) {
  const { data: nodos = [] } = useAssetNodes(hospital || null)
  if (role === 'ADMIN') {
    return <p className="text-xs text-gray-500">El administrador ve todos los hospitales.</p>
  }
  const esCliente = role === 'CLI'
  const ordenados = [...nodos].filter((n) => n.is_active).sort((a, b) => a.path.localeCompare(b.path))
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div>
        <label className={labelCls}>
          {esCliente ? <>Hospital <span className="text-red-400">*</span></> : 'Limitar a un hospital'}
        </label>
        <select
          value={hospital}
          onChange={(e) => onChange({ hospital: e.target.value, scope_node: '' })}
          className={inputCls}
        >
          <option value="">{esCliente ? 'Selecciona un hospital' : 'Todos los hospitales'}</option>
          {hospitals.map((h) => (
            <option key={h.id} value={h.id}>{h.name}</option>
          ))}
        </select>
        {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      </div>
      <div>
        <label className={labelCls}>Parte del hospital</label>
        <select
          value={scopeNode}
          disabled={!hospital}
          onChange={(e) => onChange({ scope_node: e.target.value })}
          className={`${inputCls} disabled:bg-gray-50 disabled:text-gray-400`}
        >
          <option value="">Todo el hospital</option>
          {ordenados.map((n) => (
            <option key={n.id} value={n.id}>
              {'\u00a0\u00a0'.repeat(n.path.split('/').length - 1)}{n.name}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-gray-500">Incluye lo que cuelga de la ubicación elegida.</p>
      </div>
    </div>
  )
}

// ── Actividad reciente (PASO 4) ──────────────────────────────────────────────

function RecentActivity({ userId }) {
  // El backend pagina con page_size, no con limit.
  const { data, isLoading, isError } = useAuditLog({ user_id: userId, page_size: 5 })
  const rows = data?.results ?? []

  if (isLoading) {
    return (
      <div className="flex justify-center py-6">
        <Spinner className="h-5 w-5 text-brand" />
      </div>
    )
  }
  if (isError) {
    return <p className="text-sm text-red-500">No se pudo cargar la actividad.</p>
  }
  if (rows.length === 0) {
    return <p className="text-sm text-gray-500">Sin actividad reciente</p>
  }

  return (
    <ul className="divide-y divide-gray-100">
      {rows.slice(0, 5).map((log) => (
        <li key={log.id} className="py-2 flex items-baseline justify-between gap-3">
          <span className="text-sm text-gray-700">
            <span className="font-medium">{ACTION_LABELS[log.action] ?? log.action}</span>{' '}
            <span className="text-gray-500">{entityTypeLabel(log.entity_type)}</span>
          </span>
          <span className="text-xs text-gray-500 whitespace-nowrap">
            {formatDateTime(log.timestamp)}
          </span>
        </li>
      ))}
    </ul>
  )
}

// ── Modal de edicion (PASO 4) ────────────────────────────────────────────────

function EditUserModal({ user, hospitals, currentUserId, onClose, onSaved }) {
  const update = useUpdateUser()
  const [form, setForm] = useState({
    first_name: user.first_name ?? '',
    last_name: user.last_name ?? '',
    phone: user.phone ?? '',
    employee_code: user.employee_code ?? '',
    hospital: user.hospital ?? '',
    scope_node: user.scope_node ?? '',
    is_active: user.is_active,
  })
  const [apiError, setApiError] = useState('')

  const isSelf = user.id === currentUserId
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  function handleSubmit(e) {
    e.preventDefault()
    setApiError('')
    update.mutate(
      {
        id: user.id,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: form.phone.trim(),
        employee_code: form.employee_code.trim(),
        hospital: user.role !== 'ADMIN' ? form.hospital || null : null,
        scope_node: user.role !== 'ADMIN' ? form.scope_node || null : null,
        is_active: form.is_active,
      },
      {
        onSuccess: () => onSaved(),
        onError: (err) => {
          // El error del alcance ya sale junto a su campo (AlcanceFields).
          if (fieldError(err, 'hospital') || fieldError(err, 'scope_node')) return
          setApiError(generalError(err, 'No se pudieron guardar los cambios.'))
        },
      }
    )
  }

  return (
    <Modal title={`${user.first_name} ${user.last_name}`} onClose={onClose} wide>
      <div className="space-y-6">
        <section>
          <h3 className="text-xs font-semibold text-gray-500 border-b border-gray-200 pb-2 mb-4">
            Informacion
          </h3>

          <div className="flex flex-wrap items-center gap-3 mb-4 text-sm">
            <RoleBadge role={user.role} />
            <span className="text-gray-500">{user.email}</span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Nombre</label>
                <input type="text" value={form.first_name} onChange={set('first_name')} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Apellido</label>
                <input type="text" value={form.last_name} onChange={set('last_name')} className={inputCls} />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Telefono</label>
                <input type="text" value={form.phone} onChange={set('phone')} className={inputCls} />
              </div>
              {user.role === 'TEC' && (
                <div>
                  <label className={labelCls}>Codigo de empleado</label>
                  <input
                    type="text"
                    value={form.employee_code}
                    onChange={set('employee_code')}
                    className={inputCls}
                  />
                </div>
              )}
            </div>

            <AlcanceFields
              role={user.role}
              hospitals={hospitals}
              hospital={form.hospital}
              scopeNode={form.scope_node}
              error={fieldError(update.error, 'hospital') || fieldError(update.error, 'scope_node')}
              onChange={(cambios) => setForm((f) => ({ ...f, ...cambios }))}
            />

            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={form.is_active}
                disabled={isSelf}
                onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                className="rounded border-gray-300 text-brand focus:ring-brand/30 disabled:opacity-50"
              />
              Usuario activo
              {isSelf && <span className="text-xs text-gray-500">(no puedes desactivarte a ti mismo)</span>}
            </label>

            <p className="text-xs text-gray-500">
              El rol no se edita desde aqui.
            </p>

            {apiError && <p className="text-sm text-red-600">{apiError}</p>}

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={update.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand/90 disabled:opacity-60"
              >
                {update.isPending && <Spinner />}
                {update.isPending ? 'Guardando...' : 'Guardar cambios'}
              </button>
            </div>
          </form>
        </section>

        <section>
          <h3 className="text-xs font-semibold text-gray-500 border-b border-gray-200 pb-2 mb-3">
            Actividad reciente
          </h3>
          <RecentActivity userId={user.id} />
          <Link
            to={`/auditoria?user_id=${user.id}`}
            className="inline-block mt-3 text-sm text-brand hover:underline"
          >
            Ver historial completo
          </Link>
        </section>
      </div>
    </Modal>
  )
}

// ── Pagina (PASO 2) ──────────────────────────────────────────────────────────

export default function UsersPage() {
  const { user: currentUser } = useAuthStore()
  const isAdmin = currentUser?.role === 'ADMIN'

  // El backend ignora role/is_active/search en /api/users/, asi que se pide la
  // lista completa una vez y se filtra en memoria.
  const { data: users, isLoading, isError } = useUsers()
  const { data: hospitalsData } = useHospitals({ is_active: true })

  const deactivate = useDeactivateUser()
  const update = useUpdateUser()
  const resetPassword = useResetPassword()

  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [confirming, setConfirming] = useState(null) // {id, kind}
  const [notice, setNotice] = useState('')
  const [rowError, setRowError] = useState('')

  const hospitals = useMemo(
    () => (Array.isArray(hospitalsData) ? hospitalsData : hospitalsData?.results ?? []),
    [hospitalsData]
  )
  const hospitalNames = useMemo(
    () => Object.fromEntries(hospitals.map((h) => [h.id, h.name])),
    [hospitals]
  )

  const allUsers = useMemo(
    () => (Array.isArray(users) ? users : users?.results ?? []),
    [users]
  )

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return allUsers.filter((u) => {
      if (role && u.role !== role) return false
      if (!showInactive && !u.is_active) return false
      if (!q) return true
      const haystack = `${u.first_name} ${u.last_name} ${u.email}`.toLowerCase()
      return haystack.includes(q)
    })
  }, [allUsers, role, showInactive, search])

  function flash(message) {
    setNotice(message)
    setTimeout(() => setNotice(''), NOTICE_MS)
  }

  function handleReset(target) {
    setRowError('')
    resetPassword.mutate(
      { id: target.id },
      {
        onSuccess: () => {
          setConfirming(null)
          flash(`Contrasena restablecida. Se envio el correo a ${target.email}`)
        },
        onError: (err) => {
          setConfirming(null)
          setRowError(generalError(err, 'No se pudo restablecer la contrasena.'))
        },
      }
    )
  }

  function handleToggleActive(target) {
    setRowError('')
    const onSuccess = () => {
      setConfirming(null)
      flash(
        target.is_active
          ? `${target.email} fue desactivado.`
          : `${target.email} fue activado.`
      )
    }
    const onError = (err) => {
      setConfirming(null)
      setRowError(generalError(err, 'No se pudo cambiar el estado del usuario.'))
    }

    // Desactivar tiene endpoint propio; reactivar solo existe via PATCH.
    if (target.is_active) {
      deactivate.mutate({ id: target.id }, { onSuccess, onError })
    } else {
      update.mutate({ id: target.id, is_active: true }, { onSuccess, onError })
    }
  }

  const togglePending = deactivate.isPending || update.isPending

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Gestión de usuarios</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {filtered.length} de {allUsers.length} usuarios
          </p>
        </div>
        {isAdmin && (
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand/90 transition-colors"
          >
            Nuevo usuario
          </button>
        )}
      </div>

      {notice && (
        <div className="px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-green-800 text-sm">
          {notice}
        </div>
      )}
      {rowError && (
        <div className="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {rowError}
        </div>
      )}

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-card p-4">
        <div className="flex flex-wrap gap-3 items-center">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nombre o email"
            className={`${inputCls} w-64`}
          />
          <select value={role} onChange={(e) => setRole(e.target.value)} className={`${inputCls} w-48`}>
            <option value="">Todos los roles</option>
            {Object.entries(ROLE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="rounded border-gray-300 text-brand focus:ring-brand/30"
            />
            Mostrar inactivos
          </label>
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Spinner className="h-8 w-8 text-brand" />
          </div>
        ) : isError ? (
          <div className="text-center py-16 text-sm text-red-500">
            No se pudo cargar la lista de usuarios.
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-sm text-gray-500">
            No hay usuarios que coincidan con los filtros aplicados
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr className="text-left text-xs font-medium text-gray-500">
                  <th className="px-4 py-3">Nombre completo</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Rol</th>
                  <th className="px-4 py-3">Alcance</th>
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map((u) => {
                  const isSelf = u.id === currentUser?.id
                  const confirmKind = confirming?.id === u.id ? confirming.kind : null

                  return (
                    <tr key={u.id} className="hover:bg-gray-50 align-top">
                      <td className="px-4 py-3 text-gray-800">
                        {u.full_name || `${u.first_name} ${u.last_name}`.trim()}
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-xs">{u.email}</td>
                      <td className="px-4 py-3">
                        <RoleBadge role={u.role} />
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-xs">
                        {u.role === 'ADMIN' || !u.hospital ? (
                          <span className="text-gray-400">Todos</span>
                        ) : (
                          <>
                            {hospitalNames[u.hospital] ?? '—'}
                            {u.scope_node_path && (
                              <span className="block text-gray-400">{u.scope_node_path}</span>
                            )}
                          </>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <StatusCell active={u.is_active} />
                      </td>
                      <td className="px-4 py-3">
                        {confirmKind === 'reset' ? (
                          <InlineConfirm
                            message="Se enviara una contrasena temporal al correo del usuario. Confirmar?"
                            confirmLabel="Restablecer"
                            pending={resetPassword.isPending}
                            onConfirm={() => handleReset(u)}
                            onCancel={() => setConfirming(null)}
                          />
                        ) : confirmKind === 'toggle' ? (
                          <InlineConfirm
                            message={
                              u.is_active
                                ? `Se desactivara a ${u.email} y no podra iniciar sesion. Confirmar?`
                                : `Se reactivara a ${u.email}. Confirmar?`
                            }
                            confirmLabel={u.is_active ? 'Desactivar' : 'Activar'}
                            danger={u.is_active}
                            pending={togglePending}
                            onConfirm={() => handleToggleActive(u)}
                            onCancel={() => setConfirming(null)}
                          />
                        ) : (
                          <div className="flex items-center justify-end gap-1">
                            <button
                              type="button"
                              onClick={() => setEditing(u)}
                              className="px-2.5 py-1 text-xs text-gray-600 rounded border border-gray-200 hover:bg-gray-50"
                            >
                              Ver
                            </button>
                            {isAdmin && (
                              <>
                                <button
                                  type="button"
                                  onClick={() => setConfirming({ id: u.id, kind: 'reset' })}
                                  title="Restablecer contrasena"
                                  aria-label={`Restablecer contrasena de ${u.email}`}
                                  className="p-1.5 text-gray-500 rounded border border-gray-200 hover:bg-gray-50 hover:text-gray-700"
                                >
                                  <Icon name="key" className="w-4 h-4" />
                                </button>
                                <button
                                  type="button"
                                  disabled={isSelf}
                                  title={
                                    isSelf
                                      ? 'No puedes desactivar tu propia cuenta'
                                      : u.is_active
                                        ? 'Desactivar usuario'
                                        : 'Activar usuario'
                                  }
                                  onClick={() => setConfirming({ id: u.id, kind: 'toggle' })}
                                  className={`px-2.5 py-1 text-xs rounded border disabled:opacity-40 disabled:cursor-not-allowed ${
                                    u.is_active
                                      ? 'text-red-600 border-red-200 hover:bg-red-50'
                                      : 'text-green-700 border-green-200 hover:bg-green-50'
                                  }`}
                                >
                                  {u.is_active ? 'Desactivar' : 'Activar'}
                                </button>
                              </>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {createOpen && (
        <CreateUserModal
          hospitals={hospitals}
          onClose={() => setCreateOpen(false)}
          onCreated={(email) => {
            setCreateOpen(false)
            flash(`Usuario creado. Se envio el correo de bienvenida a ${email}`)
          }}
        />
      )}

      {editing && (
        <EditUserModal
          user={editing}
          hospitals={hospitals}
          currentUserId={currentUser?.id}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            flash('Cambios guardados.')
          }}
        />
      )}
    </div>
  )
}
