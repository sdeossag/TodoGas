import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  useMaintenancePlan,
  useCreateMaintenancePlan,
  useUpdateMaintenancePlan,
} from '../../api/maintenance'
import { useHospitals, useAssets } from '../../api/assets'
import { useChecklistTemplates } from '../../api/checklists'
import Icon from '../../components/ui/Icon'

function Spinner() {
  return (
    <svg className="animate-spin h-5 w-5 text-brand" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

function calculateNextDates(frequencyValue, frequencyUnit, count = 5) {
  const fv = parseInt(frequencyValue, 10)
  if (!fv || fv <= 0) return []
  const dates = []
  let current = new Date()
  current.setHours(0, 0, 0, 0)
  for (let i = 0; i < count; i++) {
    switch (frequencyUnit) {
      case 'DAYS':   current = new Date(current); current.setDate(current.getDate() + fv); break
      case 'WEEKS':  current = new Date(current); current.setDate(current.getDate() + fv * 7); break
      case 'MONTHS': current = new Date(current); current.setMonth(current.getMonth() + fv); break
      case 'YEARS':  current = new Date(current); current.setFullYear(current.getFullYear() + fv); break
      default:       return dates
    }
    dates.push(new Date(current))
  }
  return dates
}

function formatDateShort(d) {
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' })
}

const EMPTY_FORM = {
  name: '',
  description: '',
  task_type: 'PREVENTIVE',
  priority: 'MEDIUM',
  frequency_value: 6,
  frequency_unit: 'MONTHS',
  dur_hours: '',
  dur_minutes: '',
  checklist_template: '',
  restrict_to_hospital: '',
  is_active: true,
}

export default function MaintenancePlanFormPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = !!id

  const { data: existing, isLoading: loadingExisting } = useMaintenancePlan(id)
  const createMut = useCreateMaintenancePlan()
  const updateMut = useUpdateMaintenancePlan(id)

  const { data: hospitals = [] } = useHospitals({ is_active: true })
  const { data: checklists = [] } = useChecklistTemplates({ is_active: true })

  const [form, setForm] = useState(EMPTY_FORM)
  const [selectedAssets, setSelectedAssets] = useState([])
  const [assetSearch, setAssetSearch] = useState('')
  const [assetSearchInput, setAssetSearchInput] = useState('')
  const [error, setError] = useState('')

  const { data: searchedAssets = [] } = useAssets(
    assetSearch ? { search: assetSearch } : {}
  )

  useEffect(() => {
    if (isEdit && existing) {
      const dur = existing.estimated_duration
      let dur_hours = '', dur_minutes = ''
      if (dur) {
        const match = String(dur).match(/(\d+):(\d+):(\d+)/)
        if (match) { dur_hours = match[1]; dur_minutes = match[2] }
      }
      setForm({
        name: existing.name ?? '',
        description: existing.description ?? '',
        task_type: existing.task_type ?? 'PREVENTIVE',
        priority: existing.priority ?? 'MEDIUM',
        frequency_value: existing.frequency_value ?? 6,
        frequency_unit: existing.frequency_unit ?? 'MONTHS',
        dur_hours,
        dur_minutes,
        checklist_template: existing.checklist_template?.id ?? '',
        restrict_to_hospital: existing.restrict_to_hospital?.id ?? '',
        is_active: existing.is_active ?? true,
      })
      setSelectedAssets(existing.assets ?? [])
    }
  }, [isEdit, existing])

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  function addAsset(asset) {
    if (selectedAssets.find((a) => a.id === asset.id)) return
    setSelectedAssets((prev) => [...prev, asset])
  }

  function removeAsset(assetId) {
    setSelectedAssets((prev) => prev.filter((a) => a.id !== assetId))
  }

  function buildDuration() {
    const h = parseInt(form.dur_hours, 10) || 0
    const m = parseInt(form.dur_minutes, 10) || 0
    if (h === 0 && m === 0) return null
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00`
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (!form.name.trim()) { setError('El nombre es requerido.'); return }
    if (selectedAssets.length === 0) { setError('Debes seleccionar al menos un activo.'); return }
    if (!form.frequency_value || form.frequency_value <= 0) { setError('La frecuencia debe ser mayor a 0.'); return }

    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      task_type: form.task_type,
      priority: form.priority,
      frequency_value: parseInt(form.frequency_value, 10),
      frequency_unit: form.frequency_unit,
      estimated_duration: buildDuration(),
      checklist_template: form.checklist_template || null,
      restrict_to_hospital: form.restrict_to_hospital || null,
      is_active: form.is_active,
      assets: selectedAssets.map((a) => a.id),
    }

    try {
      const result = isEdit
        ? await updateMut.mutateAsync(payload)
        : await createMut.mutateAsync(payload)
      navigate(`/planes-pm/${result.id}`)
    } catch (err) {
      const data = err?.response?.data
      if (data && typeof data === 'object') {
        setError(Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : v}`).join(' | '))
      } else {
        setError('Error al guardar el plan.')
      }
    }
  }

  const nextDates = calculateNextDates(form.frequency_value, form.frequency_unit)

  if (isEdit && loadingExisting) {
    return <div className="flex justify-center py-20"><Spinner /></div>
  }

  const isPending = createMut.isPending || updateMut.isPending

  return (
    <div className="max-w-5xl space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/planes-pm')} className="text-gray-500 hover:text-gray-600" aria-label="Volver a planes"><Icon name="arrowLeft" className="w-5 h-5" /></button>
        <h1 className="text-2xl font-bold text-gray-800">
          {isEdit ? 'Editar plan de mantenimiento' : 'Nuevo plan de mantenimiento'}
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Columna izquierda */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-4">
            <h2 className="text-sm font-semibold text-gray-600 border-b pb-2">Configuración del plan</h2>

            <Field label="Nombre *">
              <input value={form.name} onChange={set('name')} required
                placeholder="Ej: Mantenimiento preventivo cilindros O₂"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30" />
            </Field>

            <Field label="Descripción">
              <textarea value={form.description} onChange={set('description')} rows={2}
                placeholder="Descripción opcional..."
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 resize-none" />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Tipo de tarea *">
                <select value={form.task_type} onChange={set('task_type')}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none">
                  <option value="PREVENTIVE">Preventivo</option>
                  <option value="CORRECTIVE">Correctivo</option>
                  <option value="VERIFICATION">Verificación</option>
                  <option value="INSTALLATION">Instalación</option>
                  <option value="DELIVERY">Entrega</option>
                </select>
              </Field>

              <Field label="Prioridad *">
                <select value={form.priority} onChange={set('priority')}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none">
                  <option value="HIGH">Alta</option>
                  <option value="MEDIUM">Media</option>
                  <option value="LOW">Baja</option>
                </select>
              </Field>
            </div>

            <Field label="Frecuencia *">
              <div className="flex gap-2">
                <input type="number" min="1" value={form.frequency_value}
                  onChange={set('frequency_value')}
                  className="w-24 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30" />
                <select value={form.frequency_unit} onChange={set('frequency_unit')}
                  className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none">
                  <option value="DAYS">Días</option>
                  <option value="WEEKS">Semanas</option>
                  <option value="MONTHS">Meses</option>
                  <option value="YEARS">Años</option>
                </select>
              </div>
            </Field>

            <Field label="Duración estimada">
              <div className="flex gap-2 items-center">
                <input type="number" min="0" max="999" value={form.dur_hours}
                  onChange={set('dur_hours')} placeholder="0"
                  className="w-20 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none" />
                <span className="text-sm text-gray-500">h</span>
                <input type="number" min="0" max="59" value={form.dur_minutes}
                  onChange={set('dur_minutes')} placeholder="0"
                  className="w-20 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none" />
                <span className="text-sm text-gray-500">min</span>
              </div>
            </Field>

            <Field label="Checklist">
              <select value={form.checklist_template} onChange={set('checklist_template')}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none">
                <option value="">Sin checklist</option>
                {checklists.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </Field>

            <Field label="Restringir a hospital">
              <select value={form.restrict_to_hospital} onChange={set('restrict_to_hospital')}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none">
                <option value="">Todos los hospitales</option>
                {hospitals.map((h) => (
                  <option key={h.id} value={h.id}>{h.name}</option>
                ))}
              </select>
            </Field>
          </div>

          {/* Columna derecha — activos */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-4">
            <h2 className="text-sm font-semibold text-gray-600 border-b pb-2">
              Activos del plan <span className="text-red-500">*</span>
            </h2>

            {/* Buscador */}
            <div className="flex gap-2">
              <input
                value={assetSearchInput}
                onChange={(e) => setAssetSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), setAssetSearch(assetSearchInput))}
                placeholder="Buscar activo por código o nombre..."
                className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
              />
              <button type="button" onClick={() => setAssetSearch(assetSearchInput)}
                className="px-3 py-2 bg-brand text-white text-sm rounded-lg hover:bg-brand-light">
                Buscar
              </button>
            </div>

            {/* Resultados de búsqueda */}
            {assetSearch && searchedAssets.length > 0 && (
              <div className="border border-gray-100 rounded-lg max-h-40 overflow-y-auto divide-y divide-gray-50">
                {searchedAssets.slice(0, 10).map((a) => {
                  const already = selectedAssets.find((s) => s.id === a.id)
                  return (
                    <div key={a.id} className="flex items-center justify-between px-3 py-2 hover:bg-gray-50">
                      <div>
                        <p className="text-sm text-gray-800">{a.name}</p>
                        <p className="text-xs text-gray-500">{a.code} · {a.hospital?.name}</p>
                      </div>
                      <button type="button" onClick={() => addAsset(a)}
                        disabled={!!already}
                        className={`text-xs px-2 py-1 rounded ${
                          already
                            ? 'text-gray-400 cursor-not-allowed'
                            : 'bg-brand/10 text-brand hover:bg-brand/20'
                        }`}>
                        {already ? 'Ya agregado' : '+ Agregar'}
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
            {assetSearch && searchedAssets.length === 0 && (
              <p className="text-xs text-gray-500 text-center py-2">Sin resultados para "{assetSearch}"</p>
            )}

            {/* Lista seleccionados */}
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">
                Activos seleccionados ({selectedAssets.length})
              </p>
              {selectedAssets.length === 0 ? (
                <p className="text-xs text-gray-500 text-center py-4">Sin activos seleccionados</p>
              ) : (
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {selectedAssets.map((a) => (
                    <div key={a.id} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                      <div>
                        <p className="text-sm text-gray-800">{a.name}</p>
                        <p className="text-xs text-gray-500">{a.code} · {a.hospital_name ?? a.hospital?.name}</p>
                      </div>
                      <button type="button" onClick={() => removeAsset(a.id)}
                        className="text-gray-500 hover:text-red-500 text-lg leading-none ml-2">
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Próximas fechas */}
        {nextDates.length > 0 && (
          <div className="bg-brand/5 border border-brand/10 rounded-xl p-4">
            <p className="text-xs font-semibold text-brand uppercase tracking-wide mb-2">Próximas ejecuciones</p>
            <div className="flex gap-3 flex-wrap">
              {nextDates.map((d, i) => (
                <span key={i} className="text-xs bg-white border border-brand/20 text-brand px-2 py-1 rounded-lg">
                  {i + 1}. {formatDateShort(d)}
                </span>
              ))}
            </div>
          </div>
        )}

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <div className="flex justify-end gap-3 pb-4">
          <button type="button" onClick={() => navigate('/planes-pm')}
            className="px-5 py-2 text-sm text-gray-600 hover:text-gray-800">
            Cancelar
          </button>
          <button type="submit" disabled={isPending}
            className="px-6 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60 flex items-center gap-2">
            {isPending && <Spinner />}
            {isEdit ? 'Guardar cambios' : 'Crear plan'}
          </button>
        </div>
      </form>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
    </div>
  )
}
