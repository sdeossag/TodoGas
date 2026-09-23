import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateWorkOrder } from '../../api/workOrders'
import { useAssets, useAssetTree, useHospitals } from '../../api/assets'
import { useUsers } from '../../api/users'
import { useChecklistTemplates } from '../../api/checklists'
import { AvisoSinContrato } from '../../components/contracts/ContractStatus'
import Icon from '../../components/ui/Icon'
import { fieldLabel } from '../../constants/labels'
import Spinner from '../../components/ui/Spinner'
import { flattenTree, indentedLabel } from '../../utils/locationTree'


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

// ── Formulario ───────────────────────────────────────────────────────────────

/**
 * Alta manual de una OT (correctivos y verificaciones).
 *
 * Una OT es una visita a un hospital y puede cubrir varios activos: se elige
 * hospital, se filtra por ubicación y se marcan los activos, cada uno con su
 * checklist. La ubicación de la visita viaja con la OT para que el técnico sepa
 * a dónde va.
 */
export default function CreateWorkOrderPage() {
  const navigate = useNavigate()
  const createMut = useCreateWorkOrder()

  const { data: hospitals = [] } = useHospitals({ is_active: true })
  // El endpoint /api/users/ no filtra por rol — filtramos client-side
  const tecUsers = (useUsers({}).data ?? []).filter((u) => u.role === 'TEC' && u.is_active)

  // Solo sirven las plantillas con una version publicada: la tarea se ata a la
  // version, no a la plantilla.
  const { data: checklistTemplates = [] } = useChecklistTemplates({ is_active: true })
  const publishedChecklists = checklistTemplates.filter((t) => t.current_version_id)

  const [hospital, setHospital] = useState('')
  const [node, setNode] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  // activo elegido -> version de checklist ('' = sin checklist)
  const [elegidos, setElegidos] = useState(() => new Map())

  const { data: tree = [] } = useAssetTree(hospital)
  const nodos = useMemo(() => flattenTree(tree), [tree])

  const { data: assets = [], isFetching } = useAssets(
    {
      hospital_id: hospital,
      status: 'ACTIVE',
      ...(node && { node_id: node, include_sublocations: true }),
      ...(search && { search }),
    },
    { enabled: !!hospital }
  )

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

  function toggle(asset) {
    setElegidos((prev) => {
      const next = new Map(prev)
      if (next.has(asset.id)) next.delete(asset.id)
      else next.set(asset.id, { asset, version: '' })
      return next
    })
    if (errors.tasks) setErrors((e) => ({ ...e, tasks: null }))
  }

  function setChecklist(assetId, version) {
    setElegidos((prev) => {
      const next = new Map(prev)
      const actual = next.get(assetId)
      if (actual) next.set(assetId, { ...actual, version })
      return next
    })
  }

  const marcados = [...elegidos.values()]
  const todosMarcados = assets.length > 0 && assets.every((a) => elegidos.has(a.id))

  function toggleTodos() {
    setElegidos((prev) => {
      const next = new Map(prev)
      for (const a of assets) {
        if (todosMarcados) next.delete(a.id)
        else if (!next.has(a.id)) next.set(a.id, { asset: a, version: '' })
      }
      return next
    })
  }

  function validate() {
    const errs = {}
    if (marcados.length === 0) errs.tasks = 'Marca al menos un activo'
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
      tasks: marcados.map(({ asset, version }) => ({
        asset: asset.id,
        ...(version && { checklist_version: version }),
      })),
      task_type: form.task_type,
      title: form.title.trim(),
      description: form.description.trim(),
      priority: form.priority,
      scheduled_date: form.scheduled_date,
      notes: form.notes.trim(),
      ...(node && { location: node }),
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
          fieldErrors[k] = Array.isArray(v) ? JSON.stringify(v[0]) : String(v)
        })
        setErrors(fieldErrors)
      } else {
        setErrors({ _general: typeof detail === 'string' ? detail : 'Error al crear la OT. Revisa los campos.' })
      }
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/ordenes')} className="text-gray-500 hover:text-gray-600" aria-label="Volver a ordenes">
          <Icon name="arrowLeft" className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Nueva orden de trabajo</h1>
          <p className="text-sm text-gray-500">Solo OT correctivas y de verificación</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 shadow-card p-6 space-y-5">
        {/* Banner de error general */}
        {Object.keys(errors).some((k) => errors[k]) && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm font-semibold text-red-700 mb-1">No se pudo crear la OT:</p>
            <ul className="text-sm text-red-600 space-y-0.5 list-disc list-inside">
              {Object.entries(errors).map(([k, v]) => v && (
                <li key={k}>
                  {k === '_general' ? String(v) : <><span className="font-medium">{fieldLabel(k)}:</span> {String(v)}</>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Hospital y ubicacion de la visita */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Hospital" required>
            <select
              value={hospital}
              onChange={(e) => { setHospital(e.target.value); setNode(''); setElegidos(new Map()) }}
              className={INPUT}
            >
              <option value="">Elige un hospital</option>
              {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
            </select>
          </Field>
          <Field label="Ubicación" hint="Incluye lo que tiene dentro. Queda como la ubicación de la visita.">
            <select value={node} onChange={(e) => setNode(e.target.value)} disabled={!hospital} className={INPUT}>
              <option value="">Todo el hospital</option>
              {nodos.map((n) => <option key={n.id} value={n.id}>{indentedLabel(n.name, n.depth)}</option>)}
            </select>
          </Field>
        </div>

        {hospital && <AvisoSinContrato hospitalId={hospital} />}

        {/* Activos de la visita */}
        <Field label="Activos" required hint="Una OT puede cubrir varios activos del mismo hospital.">
          <div className="flex gap-2 mb-2">
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); setSearch(searchInput.trim()) } }}
              disabled={!hospital}
              placeholder="Código o nombre"
              aria-label="Buscar activo"
              className={INPUT}
            />
            <button
              type="button"
              onClick={() => setSearch(searchInput.trim())}
              disabled={!hospital}
              className="px-3 py-2 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              Buscar
            </button>
          </div>

          <div className="border border-gray-100 rounded-lg max-h-72 overflow-y-auto">
            {!hospital ? (
              <p className="text-sm text-gray-500 text-center py-8">Elige un hospital para ver sus activos.</p>
            ) : isFetching && assets.length === 0 ? (
              <div className="flex justify-center py-8"><Spinner /></div>
            ) : assets.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">No hay activos activos con este filtro.</p>
            ) : (
              <>
                <label className="flex items-center gap-2 px-3 py-2 border-b border-gray-100 text-xs text-gray-500">
                  <input type="checkbox" checked={todosMarcados} onChange={toggleTodos} />
                  Marcar los {assets.length} de esta lista
                </label>
                {assets.map((a) => (
                  <label key={a.id} className="flex items-start gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={elegidos.has(a.id)}
                      onChange={() => toggle(a)}
                      className="mt-1"
                    />
                    <span className="min-w-0">
                      <span className="block text-sm text-gray-800 truncate">
                        <span className="font-mono text-xs text-gray-500">{a.code}</span> {a.name}
                      </span>
                      <span className="block text-xs text-gray-500 truncate">{a.node?.path || 'Sin ubicación'}</span>
                    </span>
                  </label>
                ))}
              </>
            )}
          </div>
          {errors.tasks && <p className="text-red-500 text-xs mt-1">{errors.tasks}</p>}
        </Field>

        {/* Checklist de cada activo marcado */}
        {marcados.length > 0 && (
          <div className="bg-brand/5 border border-brand/20 rounded-lg p-3 space-y-2">
            <p className="text-sm font-medium text-gray-700">
              {marcados.length} activo{marcados.length !== 1 ? 's' : ''} en esta OT
            </p>
            <p className="text-xs text-gray-500">
              {publishedChecklists.length === 0
                ? 'No hay plantillas de checklist con una versión publicada.'
                : 'Cada activo puede llevar su propio checklist.'}
            </p>
            {marcados.map(({ asset, version }) => (
              <div key={asset.id} className="flex items-center gap-2 flex-wrap">
                <span className="text-sm text-gray-700 flex-1 min-w-[12rem] truncate">
                  <span className="font-mono text-xs text-gray-500">{asset.code}</span> {asset.name}
                </span>
                <select
                  value={version}
                  onChange={(e) => setChecklist(asset.id, e.target.value)}
                  disabled={publishedChecklists.length === 0}
                  aria-label={`Checklist de ${asset.code}`}
                  className={`${INPUT} w-auto max-w-[16rem] text-sm`}
                >
                  <option value="">Sin checklist</option>
                  {publishedChecklists.map((t) => (
                    <option key={t.id} value={t.current_version_id}>
                      {t.name} (v{t.current_version_number})
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => toggle(asset)}
                  className="text-gray-400 hover:text-red-600"
                  aria-label={`Quitar ${asset.code} de la OT`}
                >
                  <Icon name="close" className="w-4 h-4" />
                </button>
              </div>
            ))}
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
                className={`relative flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border rounded-lg cursor-pointer text-sm font-medium transition-colors ${
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
        <Field label="Duración estimada" hint="Opcional. Es la de la visita completa.">
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
