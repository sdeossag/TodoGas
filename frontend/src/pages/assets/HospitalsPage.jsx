import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import {
  useHospitals,
  useCreateHospital,
  useUpdateHospital,
  useToggleHospitalActive,
} from '../../api/assets'
import Icon from '../../components/ui/Icon'

const EMPTY_FORM = {
  name: '', code: '', nit: '', city: '', department: '',
  address: '', contact_name: '', contact_phone: '', contact_email: '',
}

function HospitalModal({ hospital, onClose }) {
  const isEdit = !!hospital
  const [form, setForm] = useState(isEdit ? {
    name: hospital.name ?? '',
    code: hospital.code ?? '',
    nit: hospital.nit ?? '',
    city: hospital.city ?? '',
    department: hospital.department ?? '',
    address: hospital.address ?? '',
    contact_name: hospital.contact_name ?? '',
    contact_phone: hospital.contact_phone ?? '',
    contact_email: hospital.contact_email ?? '',
  } : EMPTY_FORM)
  const [errors, setErrors] = useState({})

  const createMut = useCreateHospital()
  const updateMut = useUpdateHospital(hospital?.id)
  const mut = isEdit ? updateMut : createMut
  const saving = mut.isPending

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
    setErrors((e) => ({ ...e, [field]: undefined }))
  }

  function validate() {
    const errs = {}
    if (!form.name.trim()) errs.name = 'El nombre es obligatorio'
    if (!form.code.trim()) errs.code = 'El código es obligatorio'
    return errs
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setErrors(errs); return }
    try {
      await mut.mutateAsync(form)
      onClose()
    } catch (err) {
      const data = err?.response?.data ?? {}
      const serverErrors = {}
      Object.entries(data).forEach(([k, v]) => {
        serverErrors[k] = Array.isArray(v) ? v.join(' ') : String(v)
      })
      setErrors(serverErrors)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">
            {isEdit ? 'Editar hospital' : 'Nuevo hospital'}
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Nombre *" error={errors.name}>
              <input value={form.name} onChange={(e) => set('name', e.target.value)}
                className={input(errors.name)} placeholder="Hospital San Juan" />
            </Field>
            <Field label="Código *" error={errors.code}>
              <input value={form.code} onChange={(e) => set('code', e.target.value)}
                className={input(errors.code)} placeholder="HSJ-01" />
            </Field>
            <Field label="NIT" error={errors.nit}>
              <input value={form.nit} onChange={(e) => set('nit', e.target.value)}
                className={input()} placeholder="900.123.456-7" />
            </Field>
            <Field label="Ciudad" error={errors.city}>
              <input value={form.city} onChange={(e) => set('city', e.target.value)}
                className={input()} placeholder="Bogotá" />
            </Field>
            <Field label="Departamento" error={errors.department}>
              <input value={form.department} onChange={(e) => set('department', e.target.value)}
                className={input()} placeholder="Cundinamarca" />
            </Field>
          </div>
          <Field label="Dirección" error={errors.address}>
            <input value={form.address} onChange={(e) => set('address', e.target.value)}
              className={input()} placeholder="Calle 10 # 5-20" />
          </Field>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide pt-2">Contacto</p>
          <div className="grid grid-cols-3 gap-4">
            <Field label="Nombre" error={errors.contact_name}>
              <input value={form.contact_name} onChange={(e) => set('contact_name', e.target.value)}
                className={input()} />
            </Field>
            <Field label="Teléfono" error={errors.contact_phone}>
              <input value={form.contact_phone} onChange={(e) => set('contact_phone', e.target.value)}
                className={input()} />
            </Field>
            <Field label="Email" error={errors.contact_email}>
              <input type="email" value={form.contact_email} onChange={(e) => set('contact_email', e.target.value)}
                className={input(errors.contact_email)} />
            </Field>
          </div>
          {errors.non_field_errors && (
            <p className="text-sm text-red-600">{errors.non_field_errors}</p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancelar
            </button>
            <button type="submit" disabled={saving}
              className="btn-primary inline-flex items-center gap-2">
              {saving && <Spinner />}
              {isEdit ? 'Guardar cambios' : 'Crear hospital'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function HospitalsPage() {
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'ADMIN'
  const navigate = useNavigate()

  const [filterActive, setFilterActive] = useState('all')
  const [search, setSearch] = useState('')
  const [modalHospital, setModalHospital] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)

  const { data: hospitals = [], isLoading } = useHospitals()
  const toggleMut = useToggleHospitalActive(modalHospital?.id ?? '')

  const filtered = hospitals
    .filter((h) => {
      if (filterActive === 'active') return h.is_active
      if (filterActive === 'inactive') return !h.is_active
      return true
    })
    .filter((h) =>
      h.name.toLowerCase().includes(search.toLowerCase()) ||
      h.code.toLowerCase().includes(search.toLowerCase())
    )

  function openNew() { setModalHospital(null); setModalOpen(true) }
  function openEdit(h) { setModalHospital(h); setModalOpen(true) }

  async function handleToggle(h) {
    await useToggleHospitalActiveFor(h.id)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Hospitales</h1>
          <p className="text-sm text-gray-500 mt-0.5">Gestión de clientes y sedes</p>
        </div>
        {isAdmin && (
          <button onClick={openNew}
            className="px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light transition-colors">
            + Nuevo hospital
          </button>
        )}
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
          {[['all', 'Todos'], ['active', 'Activos'], ['inactive', 'Inactivos']].map(([val, label]) => (
            <button key={val} onClick={() => setFilterActive(val)}
              className={`px-3 py-1.5 ${filterActive === val ? 'bg-brand text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>
              {label}
            </button>
          ))}
        </div>
        <input
          value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nombre o código..."
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 w-64"
        />
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner className="w-8 h-8 text-brand" /></div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <Icon name="hospital" className="w-10 h-10 mx-auto mb-3 text-gray-400" />
            <p className="font-medium">No hay hospitales registrados</p>
            {isAdmin && <p className="text-sm mt-1">Crea el primero con el botón "Nuevo hospital"</p>}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">Nombre</th>
                <th className="px-4 py-3">Código</th>
                <th className="px-4 py-3">Ciudad</th>
                <th className="px-4 py-3 text-center">Activos</th>
                <th className="px-4 py-3 text-center">Estado</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map((h) => (
                <HospitalRow key={h.id} hospital={h} isAdmin={isAdmin}
                  onEdit={() => openEdit(h)}
                  onViewAssets={() => navigate(`/activos?hospital_id=${h.id}`)}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modalOpen && (
        <HospitalModal hospital={modalHospital} onClose={() => setModalOpen(false)} />
      )}
    </div>
  )
}

function HospitalRow({ hospital: h, isAdmin, onEdit, onViewAssets }) {
  const toggleMut = useToggleHospitalActive(h.id)

  return (
    <tr className="hover:bg-gray-50 transition-colors">
      <td className="px-4 py-3 font-medium text-gray-800">{h.name}</td>
      <td className="px-4 py-3 text-gray-500 font-mono">{h.code}</td>
      <td className="px-4 py-3 text-gray-500">{h.city || '—'}</td>
      <td className="px-4 py-3 text-center">
        <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-50 text-brand font-semibold text-xs">
          {h.asset_count}
        </span>
      </td>
      <td className="px-4 py-3 text-center">
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
          ${h.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
          {h.is_active ? 'Activo' : 'Inactivo'}
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="flex justify-end gap-2">
          <button onClick={onViewAssets}
            className="text-xs px-2 py-1 rounded bg-brand/10 text-brand hover:bg-brand/20">
            Ver activos
          </button>
          {isAdmin && (
            <>
              <button onClick={onEdit}
                className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200">
                Editar
              </button>
              <button
                onClick={() => toggleMut.mutate()}
                disabled={toggleMut.isPending}
                className={`text-xs px-2 py-1 rounded disabled:opacity-50
                  ${h.is_active
                    ? 'bg-orange-100 text-orange-700 hover:bg-orange-200'
                    : 'bg-green-100 text-green-700 hover:bg-green-200'}`}>
                {h.is_active ? 'Desactivar' : 'Activar'}
              </button>
            </>
          )}
        </div>
      </td>
    </tr>
  )
}

// Helpers
function Field({ label, error, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
      {error && <p className="text-xs text-red-500 mt-0.5">{error}</p>}
    </div>
  )
}

function input(hasError) {
  return `input-field ${hasError ? 'border-red-400' : ''}`
}

function Spinner({ className = 'w-4 h-4 text-white' }) {
  return (
    <svg className={`animate-spin ${className}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}
