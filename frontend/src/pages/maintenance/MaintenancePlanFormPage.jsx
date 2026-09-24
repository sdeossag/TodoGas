import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  useCreateMaintenancePlan,
  useMaintenancePlan,
  useUpdateMaintenancePlan,
} from '../../api/maintenance'
import { useHospitals } from '../../api/assets'
import Icon from '../../components/ui/Icon'
import Spinner from '../../components/ui/Spinner'
import { apiErrorMessage } from '../../utils/apiError'
import { PRIORITIES } from '../../utils/maintenance'

const EMPTY_FORM = {
  name: '',
  description: '',
  priority: 'MEDIUM',
  classification_1: '',
  classification_2: '',
  restrict_to_hospital: '',
  is_active: true,
}

/**
 * Datos generales del plan de tareas. Las tareas y los activos se manejan en
 * el detalle del plan, como en Fracttal: primero se crea el plan y luego se le
 * agregan tareas y se asigna a los activos.
 */
export default function MaintenancePlanFormPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = !!id

  const { data: existing, isLoading } = useMaintenancePlan(id)
  const createMut = useCreateMaintenancePlan()
  const updateMut = useUpdateMaintenancePlan(id)
  const { data: hospitals = [] } = useHospitals({ is_active: true })

  const [form, setForm] = useState(EMPTY_FORM)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isEdit && existing) {
      setForm({
        name: existing.name ?? '',
        description: existing.description ?? '',
        priority: existing.priority ?? 'MEDIUM',
        classification_1: existing.classification_1 ?? '',
        classification_2: existing.classification_2 ?? '',
        restrict_to_hospital: existing.restrict_to_hospital?.id ?? '',
        is_active: existing.is_active ?? true,
      })
    }
  }, [isEdit, existing])

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (!form.name.trim()) { setError('El nombre es obligatorio.'); return }
    const payload = {
      ...form,
      name: form.name.trim(),
      description: form.description.trim(),
      restrict_to_hospital: form.restrict_to_hospital || null,
    }
    try {
      const result = isEdit ? await updateMut.mutateAsync(payload) : await createMut.mutateAsync(payload)
      // Un plan nuevo no hace nada hasta tener tareas: se abre en esa pestaña.
      navigate(`/planes-pm/${result.id}`, { state: isEdit ? undefined : { created: true } })
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo guardar el protocolo.'))
    }
  }

  if (isEdit && isLoading) {
    return <div className="flex justify-center py-20"><Spinner /></div>
  }

  const isPending = createMut.isPending || updateMut.isPending
  const input = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30'

  return (
    <div className="max-w-2xl space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(isEdit ? `/planes-pm/${id}` : '/planes-pm')}
          className="text-gray-500 hover:text-gray-600" aria-label="Volver">
          <Icon name="arrowLeft" className="w-5 h-5" />
        </button>
        <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">
          {isEdit ? 'Editar protocolo' : 'Nuevo protocolo'}
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 shadow-card p-5 space-y-4">
        <Field label="Nombre *" hint="Como lo reconocen en campo: «3 TOMAS», «ALARMA 3 GASES».">
          <input value={form.name} onChange={set('name')} required className={input}
            placeholder="Ej: Salidas de gases 24 tomas" />
        </Field>

        <Field label="Descripción">
          <textarea value={form.description} onChange={set('description')} rows={2}
            className={`${input} resize-none`} placeholder="Opcional" />
        </Field>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field label="Prioridad por defecto" hint="La toman las tareas nuevas del protocolo.">
            <select value={form.priority} onChange={set('priority')} className={input}>
              {PRIORITIES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </Field>
          <Field label="Solo para el hospital" hint="Vacío: se puede asignar a activos de cualquier hospital.">
            <select value={form.restrict_to_hospital} onChange={set('restrict_to_hospital')} className={input}>
              <option value="">Cualquier hospital</option>
              {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
            </select>
          </Field>
          <Field label="Clasificación 1">
            <input value={form.classification_1} onChange={set('classification_1')} className={input} />
          </Field>
          <Field label="Clasificación 2">
            <input value={form.classification_2} onChange={set('classification_2')} className={input} />
          </Field>
        </div>

        {!isEdit && (
          <p className="text-sm text-gray-600 bg-brand/5 border border-brand/10 rounded-lg px-3 py-2">
            Después de crearlo le agregas las tareas (qué se hace, con qué checklist y cada cuánto)
            y lo asignas a los activos.
          </p>
        )}

        {error && <p className="text-red-600 text-sm" role="alert">{error}</p>}

        <div className="flex justify-end gap-3 pt-1">
          <button type="button" onClick={() => navigate(isEdit ? `/planes-pm/${id}` : '/planes-pm')}
            className="px-5 py-2 text-sm text-gray-600 hover:text-gray-800">
            Cancelar
          </button>
          <button type="submit" disabled={isPending}
            className="px-6 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60 flex items-center gap-2">
            {isPending && <Spinner />}
            {isEdit ? 'Guardar cambios' : 'Crear protocolo'}
          </button>
        </div>
      </form>
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <div>
      <label className="block">
        <span className="block text-sm font-medium text-gray-700 mb-1">{label}</span>
        {children}
      </label>
      {hint && <p className="text-xs text-gray-500 mt-1">{hint}</p>}
    </div>
  )
}
