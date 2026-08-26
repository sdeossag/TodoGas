import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateWorkOrder } from '../../api/workOrders'
import { useAssets } from '../../api/assets'
import { useUsers } from '../../api/users'
import Icon from '../../components/ui/Icon'

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

function Field({ label, required, children, hint }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
      {hint && <p className="text-xs text-gray-500 mt-0.5">{hint}</p>}
    </div>
  )
}

const INPUT = 'input-field'

// ── Asset autocomplete ───────────────────────────────────────────────────────

function AssetSearch({ value, onChange }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const { data: results = [], isFetching } = useAssets(
    query.length >= 2 ? { search: query, status: 'ACTIVE' } : {}
  )

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function select(asset) {
    onChange(asset)
    setQuery(`${asset.code} — ${asset.name}`)
    setOpen(false)
  }

  function handleQueryChange(e) {
    setQuery(e.target.value)
    if (!e.target.value) onChange(null)
    setOpen(true)
  }

  return (
    <div className="relative" ref={ref}>
      <input
        value={value ? `${value.code} — ${value.name}` : query}
        onChange={handleQueryChange}
        onFocus={() => setOpen(true)}
        placeholder="Buscar por código o nombre..."
        className={INPUT}
        readOnly={!!value}
      />
      {value && (
        <button
          type="button"
          onClick={() => { onChange(null); setQuery('') }}
          className="absolute right-2 top-2 text-gray-500 hover:text-gray-600"
          aria-label="Limpiar seleccion"
        ><Icon name="close" className="w-4 h-4" /></button>
      )}
      {open && !value && query.length >= 2 && (
        <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
          {isFetching ? (
            <div className="flex justify-center p-3"><Spinner /></div>
          ) : results.length === 0 ? (
            <p className="text-sm text-gray-500 p-3 text-center">Sin resultados</p>
          ) : (
            results.map((a) => (
              <button
                key={a.id}
                type="button"
                onClick={() => select(a)}
                className="w-full text-left px-3 py-2 hover:bg-gray-50 transition-colors"
              >
                <span className="font-mono text-xs text-gray-500">{a.code}</span>
                <span className="mx-1 text-gray-400">|</span>
                <span className="text-sm text-gray-700">{a.name}</span>
                <span className="block text-xs text-gray-500">{a.hospital?.name ?? ''}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ── Main form ────────────────────────────────────────────────────────────────

export default function CreateWorkOrderPage() {
  const navigate = useNavigate()
  const createMut = useCreateWorkOrder()

  // El endpoint /api/users/ no filtra por rol — filtramos client-side
  const tecUsers = (useUsers({}).data ?? []).filter((u) => u.role === 'TEC' && u.is_active)

  const [selectedAsset, setSelectedAsset] = useState(null)
  const [form, setForm] = useState({
    task_type: 'CORRECTIVE',
    title: '',
    description: '',
    priority: 'MEDIUM',
    scheduled_date: '',
    estimated_hours: '',
    estimated_minutes: '',
    assigned_to: '',
    notes: '',
    request_number: '',
  })
  const [errors, setErrors] = useState({})

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
    if (errors[field]) setErrors((e) => ({ ...e, [field]: null }))
  }

  function validate() {
    const errs = {}
    if (!selectedAsset) errs.asset = 'Selecciona un activo'
    if (!form.title.trim()) errs.title = 'El título es requerido'
    if (!form.scheduled_date) errs.scheduled_date = 'La fecha límite es requerida'
    return errs
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length > 0) { setErrors(errs); return }

    const estimatedDuration =
      form.estimated_hours || form.estimated_minutes
        ? `${String(form.estimated_hours || '0').padStart(2, '0')}:${String(form.estimated_minutes || '0').padStart(2, '0')}:00`
        : undefined

    const payload = {
      asset: selectedAsset.id,
      task_type: form.task_type,
      title: form.title.trim(),
      description: form.description.trim(),
      priority: form.priority,
      scheduled_date: form.scheduled_date,
      notes: form.notes.trim(),
      ...(form.assigned_to && { assigned_to: form.assigned_to }),
      ...(estimatedDuration && { estimated_duration: estimatedDuration }),
      ...(form.request_number && { request_number: parseInt(form.request_number) }),
    }

    try {
      const wo = await createMut.mutateAsync(payload)
      navigate(`/ordenes/${wo.id}`)
    } catch (err) {
      const detail = err?.response?.data
      console.error('[CreateWorkOrder] 400 body:', detail)
      if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
        const fieldErrors = {}
        Object.entries(detail).forEach(([k, v]) => {
          fieldErrors[k] = Array.isArray(v) ? v[0] : String(v)
        })
        setErrors(fieldErrors)
      } else {
        setErrors({ _general: typeof detail === 'string' ? detail : 'Error al crear la OT. Revisa los campos.' })
      }
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/ordenes')} className="text-gray-500 hover:text-gray-600" aria-label="Volver a ordenes">
          <Icon name="arrowLeft" className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Nueva Orden de Trabajo</h1>
          <p className="text-sm text-gray-500">Solo OT correctivas y de verificación</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-5">
        {/* Banner de error general */}
        {Object.keys(errors).length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm font-semibold text-red-700 mb-1">No se pudo crear la OT:</p>
            <ul className="text-sm text-red-600 space-y-0.5 list-disc list-inside">
              {Object.entries(errors).map(([k, v]) => v && (
                <li key={k}><span className="font-mono text-xs">{k}:</span> {String(v)}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Activo */}
        <Field label="Activo" required>
          <AssetSearch value={selectedAsset} onChange={setSelectedAsset} />
          {errors.asset && <p className="text-red-500 text-xs mt-1">{errors.asset}</p>}
        </Field>

        {/* Info del activo seleccionado */}
        {selectedAsset && (
          <div className="bg-brand/5 border border-brand/20 rounded-lg p-3 text-sm">
            <p className="font-medium text-gray-700">
              <span className="font-mono text-xs text-gray-500">{selectedAsset.code}</span>{' '}
              {selectedAsset.name}
            </p>
            <p className="text-gray-500 text-xs mt-0.5">{selectedAsset.hospital?.name}</p>
            <p className="text-xs mt-1">
              Estado:{' '}
              <span className={selectedAsset.status === 'ACTIVE' ? 'text-green-600 font-medium' : 'text-red-500'}>
                {selectedAsset.status}
              </span>
            </p>
          </div>
        )}

        {/* Tipo de OT */}
        <Field label="Tipo de OT" required>
          <div className="flex gap-3">
            {[
              { value: 'CORRECTIVE', label: 'Correctivo' },
              { value: 'VERIFICATION', label: 'Verificación' },
            ].map(({ value, label }) => (
              <label key={value}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border rounded-lg cursor-pointer text-sm font-medium transition-colors ${
                  form.task_type === value
                    ? 'border-brand bg-brand/5 text-brand'
                    : 'border-gray-200 text-gray-500 hover:border-gray-300'
                }`}
              >
                <input type="radio" name="task_type" value={value}
                  checked={form.task_type === value}
                  onChange={() => set('task_type', value)}
                  className="sr-only"
                />
                {label}
              </label>
            ))}
          </div>
        </Field>

        {/* Título */}
        <Field label="Título" required>
          <input value={form.title} onChange={(e) => set('title', e.target.value)}
            placeholder="Ej: Mantenimiento correctivo compresor de oxígeno"
            className={INPUT} />
          {errors.title && <p className="text-red-500 text-xs mt-1">{errors.title}</p>}
        </Field>

        {/* Descripción */}
        <Field label="Descripción">
          <textarea rows={3} value={form.description} onChange={(e) => set('description', e.target.value)}
            placeholder="Detalles del trabajo a realizar..."
            className={`${INPUT} resize-none`} />
        </Field>

        {/* Prioridad y fecha */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Prioridad" required>
            <select value={form.priority} onChange={(e) => set('priority', e.target.value)} className={INPUT}>
              <option value="HIGH">Alta</option>
              <option value="MEDIUM">Media</option>
              <option value="LOW">Baja</option>
            </select>
          </Field>
          <Field label="Fecha límite" required>
            <input type="date" value={form.scheduled_date} onChange={(e) => set('scheduled_date', e.target.value)}
              className={INPUT} />
            {errors.scheduled_date && <p className="text-red-500 text-xs mt-1">{errors.scheduled_date}</p>}
          </Field>
        </div>

        {/* Duración estimada */}
        <Field label="Duración estimada" hint="Opcional">
          <div className="flex gap-2 items-center">
            <input type="number" min="0" max="999" value={form.estimated_hours}
              onChange={(e) => set('estimated_hours', e.target.value)}
              placeholder="0" className={`${INPUT} w-24`} />
            <span className="text-sm text-gray-500">h</span>
            <input type="number" min="0" max="59" value={form.estimated_minutes}
              onChange={(e) => set('estimated_minutes', e.target.value)}
              placeholder="0" className={`${INPUT} w-24`} />
            <span className="text-sm text-gray-500">min</span>
          </div>
        </Field>

        {/* Técnico asignado */}
        <Field label="Técnico asignado" hint="Opcional">
          <select value={form.assigned_to} onChange={(e) => set('assigned_to', e.target.value)} className={INPUT}>
            <option value="">Sin asignar</option>
            {tecUsers.map((u) => (
              <option key={u.id} value={u.id}>{u.first_name} {u.last_name}</option>
            ))}
          </select>
        </Field>

        {/* Checklist */}
        <Field label="Checklist" hint="Disponible en Sprint 4">
          <select disabled className={`${INPUT} opacity-50 cursor-not-allowed`}>
            <option>Sin checklist</option>
          </select>
        </Field>

        {/* Notas */}
        <Field label="Notas">
          <textarea rows={2} value={form.notes} onChange={(e) => set('notes', e.target.value)}
            placeholder="Observaciones adicionales..."
            className={`${INPUT} resize-none`} />
        </Field>

        {/* Error general */}
        {errors.non_field_errors && (
          <p className="text-red-500 text-sm">{errors.non_field_errors}</p>
        )}

        {/* Botones */}
        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={() => navigate('/ordenes')} className="btn-secondary">
            Cancelar
          </button>
          <button
            type="submit"
            disabled={createMut.isPending}
            className="btn-primary inline-flex items-center gap-2"
          >
            {createMut.isPending && <Spinner />}
            Crear OT
          </button>
        </div>
      </form>
    </div>
  )
}
