import { useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer } from 'recharts'
import useAuthStore from '../../store/authStore'
import {
  useAssignPlanAssets,
  useComplianceData,
  useCreateEventOccurrence,
  useDeletePlanTask,
  useMaintenancePlan,
  usePausePlan,
  useRemovePlanAssets,
  useResumePlan,
  useSavePlanTask,
} from '../../api/maintenance'
import { useAssets, useAssetTree, useHospitals } from '../../api/assets'
import { useChecklistTemplates } from '../../api/checklists'
import Icon from '../../components/ui/Icon'
import Modal from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import { TASK_TYPE_LABELS, taskTypeLabel } from '../../constants/labels'
import { apiErrorMessage } from '../../utils/apiError'
import { flattenTree, indentedLabel } from '../../utils/locationTree'
import {
  FREQ_UNITS,
  PRIORITIES,
  PRIORITY_BADGE,
  addFrequency,
  buildDuration,
  formatDate,
  formatDuration,
  formatFrequency,
  priorityLabel,
  relativeDue,
  splitDuration,
  todayIso,
} from '../../utils/maintenance'

const btnPrimary = 'px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60 flex items-center gap-2'
const btnGhost = 'px-4 py-2 text-sm text-gray-600 hover:text-gray-800'
const input = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30'

export default function MaintenancePlanDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'ADMIN'
  const recienCreado = !!location.state?.created

  const [tab, setTab] = useState('tareas')
  const { data: plan, isLoading, isError } = useMaintenancePlan(id)
  const pauseMut = usePausePlan(id)
  const resumeMut = useResumePlan(id)

  if (isLoading) return <div className="flex justify-center py-20"><Spinner /></div>
  if (isError || !plan) {
    return (
      <div className="text-center py-20 text-gray-500">
        <Icon name="warning" className="w-10 h-10 mx-auto mb-3 text-amber-500" />
        <p>No se encontró el plan</p>
        <button onClick={() => navigate('/planes-pm')} className="mt-3 text-sm text-brand hover:underline">Volver</button>
      </div>
    )
  }

  const tareasActivas = plan.tasks.filter((t) => t.is_active)

  return (
    <div className="space-y-5 max-w-6xl">
      <nav className="text-sm text-gray-500 flex gap-1">
        <button onClick={() => navigate('/planes-pm')} className="hover:text-brand">Planes de tareas</button>
        <span>/</span>
        <span className="text-gray-600 truncate">{plan.name}</span>
      </nav>

      <div className="bg-white rounded-xl border border-gray-200 shadow-card p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                plan.is_active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
              }`}>
                {plan.is_active ? 'Activo' : 'Pausado'}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_BADGE[plan.priority] ?? ''}`}>
                Prioridad {priorityLabel(plan.priority).toLowerCase()}
              </span>
              {plan.restrict_to_hospital && (
                <span className="text-xs text-gray-500">Solo {plan.restrict_to_hospital.name}</span>
              )}
            </div>
            <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">{plan.name}</h1>
            {plan.description && <p className="text-sm text-gray-500 mt-1">{plan.description}</p>}
          </div>
          {isAdmin && (
            <div className="flex gap-2 flex-wrap">
              <button onClick={() => navigate(`/planes-pm/${id}/editar`)}
                className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
                Editar
              </button>
              {plan.is_active ? (
                <button onClick={() => pauseMut.mutate()} disabled={pauseMut.isPending}
                  title="Mientras esté pausado sus pendientes no aparecen para planificar"
                  className="px-4 py-2 bg-yellow-50 text-yellow-700 text-sm rounded-lg hover:bg-yellow-100 disabled:opacity-50">
                  Pausar
                </button>
              ) : (
                <button onClick={() => resumeMut.mutate()} disabled={resumeMut.isPending}
                  className="px-4 py-2 bg-green-50 text-green-700 text-sm rounded-lg hover:bg-green-100 disabled:opacity-50">
                  Reanudar
                </button>
              )}
            </div>
          )}
        </div>

        <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-4 border-t pt-4">
          <InfoItem label="Tareas activas" value={tareasActivas.length} />
          <InfoItem label="Activos con este plan" value={plan.assets_count} />
          <InfoItem label="Próxima fecha"
            value={plan.next_due_date ? `${formatDate(plan.next_due_date)} (${relativeDue(plan.next_due_date)})` : '—'} />
          <InfoItem label="Pendientes vencidas"
            value={<span className={plan.overdue_count ? 'text-red-700 font-medium' : ''}>{plan.overdue_count}</span>} />
        </div>
      </div>

      {recienCreado && plan.tasks.length === 0 && (
        <div className="bg-brand/5 border border-brand/10 rounded-xl px-4 py-3 text-sm text-gray-700 flex items-center gap-2">
          <Icon name="checkCircle" className="w-4 h-4 text-green-600 flex-shrink-0" />
          Plan creado. Agrégale su primera tarea y después asígnalo a los activos.
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        <div className="border-b flex overflow-x-auto" role="tablist">
          {[
            ['tareas', `Tareas (${plan.tasks.length})`],
            ['activos', `Activos (${plan.assets_count})`],
            ['cumplimiento', 'Cumplimiento'],
          ].map(([key, label]) => (
            <button key={key} role="tab" aria-selected={tab === key} onClick={() => setTab(key)}
              className={`px-5 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                tab === key ? 'border-b-2 border-brand text-brand' : 'text-gray-500 hover:text-gray-700'
              }`}>
              {label}
            </button>
          ))}
        </div>
        <div className="p-6">
          {tab === 'tareas' && <TasksTab plan={plan} isAdmin={isAdmin} />}
          {tab === 'activos' && <AssetsTab plan={plan} isAdmin={isAdmin} />}
          {tab === 'cumplimiento' && <ComplianceTab planId={id} />}
        </div>
      </div>
    </div>
  )
}

function InfoItem({ label, value }) {
  return (
    <div>
      <p className="text-xs font-medium text-gray-500 mb-0.5">{label}</p>
      <div className="text-sm text-gray-800">{value ?? '—'}</div>
    </div>
  )
}

// ── Tareas del plan ──────────────────────────────────────────────────────────

function TasksTab({ plan, isAdmin }) {
  const [editing, setEditing] = useState(null) // {} para nueva, la tarea para editar
  const [toggling, setToggling] = useState(null)
  const [eventTask, setEventTask] = useState(null)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <p className="text-sm text-gray-500">
          Cada tarea, en cada activo del plan, lleva su propio ciclo: al cerrarse la OT se crea la siguiente.
        </p>
        {isAdmin && (
          <button onClick={() => setEditing({})} className={btnPrimary}>
            <Icon name="plus" className="w-4 h-4" /> Agregar tarea
          </button>
        )}
      </div>

      {plan.tasks.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-10">
          Este plan todavía no tiene tareas, así que no genera nada en sus activos.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr className="text-left text-xs font-medium text-gray-500">
                <th className="px-3 py-2">Tarea</th>
                <th className="px-3 py-2">Cuándo</th>
                <th className="px-3 py-2">Checklist</th>
                <th className="px-3 py-2">Duración</th>
                <th className="px-3 py-2">Abiertas / hechas</th>
                <th className="px-3 py-2 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {plan.tasks.map((t) => (
                <tr key={t.id} className={`align-top ${t.is_active ? '' : 'opacity-60'}`}>
                  <td className="px-3 py-2">
                    <p className="font-medium text-gray-800">{t.name}</p>
                    <p className="text-xs text-gray-500">
                      {taskTypeLabel(t.task_type)} · Prioridad {priorityLabel(t.priority).toLowerCase()}
                      {!t.is_active && ' · Desactivada'}
                    </p>
                  </td>
                  <td className="px-3 py-2 text-gray-600">
                    <p>{formatFrequency(t)}</p>
                    {t.trigger === 'DATE' && (
                      <p className="text-xs text-gray-500">
                        {t.fixed_schedule ? 'Programación fija' : 'Cuenta desde que se hace'}
                        {t.start_date && ` · desde ${formatDate(t.start_date)}`}
                      </p>
                    )}
                  </td>
                  <td className="px-3 py-2 text-gray-600">{t.checklist_template_name ?? <span className="text-gray-400">Sin checklist</span>}</td>
                  <td className="px-3 py-2 text-gray-600">{formatDuration(t.estimated_duration)}</td>
                  <td className="px-3 py-2 text-gray-600">{t.open_count} / {t.done_count}</td>
                  <td className="px-3 py-2">
                    {isAdmin && (
                      <div className="flex justify-end gap-1 flex-wrap">
                        {t.trigger === 'EVENT' && t.is_active && (
                          <button onClick={() => setEventTask(t)}
                            className="text-xs px-2 py-1 rounded bg-brand/10 text-brand hover:bg-brand/20">
                            Crear para un activo
                          </button>
                        )}
                        <button onClick={() => setEditing(t)}
                          className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200">
                          Editar
                        </button>
                        <button onClick={() => setToggling(t)}
                          className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200">
                          {t.is_active ? 'Desactivar' : 'Activar'}
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && <PlanTaskModal plan={plan} task={editing.id ? editing : null} onClose={() => setEditing(null)} />}
      {toggling && <ToggleTaskModal task={toggling} onClose={() => setToggling(null)} />}
      {eventTask && <EventOccurrenceModal plan={plan} task={eventTask} onClose={() => setEventTask(null)} />}
    </div>
  )
}

function emptyTask(plan) {
  return {
    name: '',
    description: '',
    task_type: 'PREVENTIVE',
    priority: plan.priority,
    checklist_template: '',
    trigger: 'DATE',
    frequency_value: 6,
    frequency_unit: 'MONTHS',
    repeat: 'always',
    repeat_count: 1,
    fixed_schedule: false,
    dur_hours: '',
    dur_minutes: '',
    start_date: todayIso(),
    block_counts: {},
  }
}

function PlanTaskModal({ plan, task, onClose }) {
  const saveMut = useSavePlanTask()
  const { data: templates = [] } = useChecklistTemplates({ is_active: true })
  const published = templates.filter((c) => c.current_version_id)
  const [error, setError] = useState('')
  const [form, setForm] = useState(() => {
    if (!task) return emptyTask(plan)
    const { hours, minutes } = splitDuration(task.estimated_duration)
    return {
      name: task.name,
      description: task.description ?? '',
      task_type: task.task_type,
      priority: task.priority,
      checklist_template: task.checklist_template ?? '',
      trigger: task.trigger,
      frequency_value: task.frequency_value ?? 6,
      frequency_unit: task.frequency_unit || 'MONTHS',
      repeat: task.repeat_count ? 'times' : 'always',
      repeat_count: task.repeat_count ?? 1,
      fixed_schedule: task.fixed_schedule,
      dur_hours: hours,
      dur_minutes: minutes,
      start_date: task.start_date ?? '',
      block_counts: task.block_counts ?? {},
    }
  })

  const set = (field) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    setForm((f) => ({ ...f, [field]: value }))
  }

  // Una plantilla elegida antes de exigir versión publicada se sigue mostrando,
  // marcada; si desapareciera, el guardado fallaría sin explicación visible.
  const huerfana = templates.find((c) => c.id === form.checklist_template && !c.current_version_id)
  const porFecha = form.trigger === 'DATE'
  // Grupos repetibles del checklist elegido: la tarea dice cuántas veces va
  // cada uno, como el plan "20 TOMAS" de Fracttal.
  const repetibles = templates.find((c) => c.id === form.checklist_template)?.current_repeatable_groups ?? []

  function setBlockCount(grupo, valor) {
    setForm((f) => ({ ...f, block_counts: { ...f.block_counts, [grupo]: valor } }))
  }

  const proximas = useMemo(() => {
    if (!porFecha || !form.start_date) return []
    const fechas = [form.start_date]
    while (fechas.length < 4) {
      const siguiente = addFrequency(fechas[fechas.length - 1], form.frequency_value, form.frequency_unit)
      if (!siguiente) break
      fechas.push(siguiente)
    }
    return form.repeat === 'times' ? fechas.slice(0, Math.max(1, parseInt(form.repeat_count, 10) || 1)) : fechas
  }, [porFecha, form.start_date, form.frequency_value, form.frequency_unit, form.repeat, form.repeat_count])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (!form.name.trim()) { setError('El nombre es obligatorio.'); return }
    if (porFecha && !(parseInt(form.frequency_value, 10) > 0)) { setError('La frecuencia debe ser mayor a 0.'); return }
    const payload = {
      ...(task ? { id: task.id } : { plan: plan.id }),
      name: form.name.trim(),
      description: form.description.trim(),
      task_type: form.task_type,
      priority: form.priority,
      checklist_template: form.checklist_template || null,
      trigger: form.trigger,
      frequency_value: porFecha ? parseInt(form.frequency_value, 10) : null,
      frequency_unit: porFecha ? form.frequency_unit : '',
      repeat_count: form.repeat === 'times' ? parseInt(form.repeat_count, 10) || 1 : null,
      fixed_schedule: porFecha && form.fixed_schedule,
      estimated_duration: buildDuration(form.dur_hours, form.dur_minutes),
      start_date: porFecha && form.start_date ? form.start_date : null,
      block_counts: Object.fromEntries(
        repetibles.map((g) => [g, Math.max(1, parseInt(form.block_counts[g], 10) || 1)])
      ),
    }
    try {
      await saveMut.mutateAsync(payload)
      onClose()
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo guardar la tarea.'))
    }
  }

  return (
    <Modal title={task ? `Editar «${task.name}»` : 'Nueva tarea del plan'} onClose={onClose} width="max-w-2xl">
      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">Nombre *</span>
          <input value={form.name} onChange={set('name')} required autoFocus className={input}
            placeholder="Ej: Preventivo semestral de salidas" />
        </label>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <label className="block">
            <span className="block text-sm font-medium text-gray-700 mb-1">Tipo</span>
            <select value={form.task_type} onChange={set('task_type')} className={input}>
              {Object.entries(TASK_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="block text-sm font-medium text-gray-700 mb-1">Prioridad</span>
            <select value={form.priority} onChange={set('priority')} className={input}>
              {PRIORITIES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </label>
          <div>
            <span className="block text-sm font-medium text-gray-700 mb-1">Duración estimada</span>
            <div className="flex items-center gap-1.5">
              <input type="number" min="0" value={form.dur_hours} onChange={set('dur_hours')} placeholder="0"
                aria-label="Horas" className="w-16 border border-gray-200 rounded-lg px-2 py-2 text-sm" />
              <span className="text-sm text-gray-500">h</span>
              <input type="number" min="0" max="59" value={form.dur_minutes} onChange={set('dur_minutes')} placeholder="0"
                aria-label="Minutos" className="w-16 border border-gray-200 rounded-lg px-2 py-2 text-sm" />
              <span className="text-sm text-gray-500">min</span>
            </div>
          </div>
        </div>

        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">Checklist</span>
          <select value={form.checklist_template} onChange={set('checklist_template')} className={input}>
            <option value="">Sin checklist</option>
            {published.map((c) => <option key={c.id} value={c.id}>{c.name} (v{c.current_version_number})</option>)}
            {huerfana && <option value={huerfana.id}>{huerfana.name} — sin versión publicada</option>}
          </select>
          <span className="block text-xs text-gray-500 mt-1">
            {huerfana
              ? 'Esa plantilla no tiene versión publicada: publícala o elige otra para poder guardar.'
              : 'Al meter la tarea en una OT se usa la versión publicada en ese momento.'}
          </span>
        </label>

        {repetibles.length > 0 && (
          <div className="border border-brand/20 bg-brand/5 rounded-lg p-3 space-y-2">
            <p className="text-sm text-gray-700">
              Este checklist tiene bloques que se repiten. ¿Cuántas veces van en esta tarea?
            </p>
            <div className="flex flex-wrap gap-4">
              {repetibles.map((g) => (
                <label key={g} className="flex items-center gap-2 text-sm text-gray-700">
                  {g}
                  <input type="number" min="1" value={form.block_counts[g] ?? ''}
                    onChange={(e) => setBlockCount(g, e.target.value)} placeholder="1"
                    aria-label={`Cantidad de ${g}`}
                    className="w-20 border border-gray-200 rounded-lg px-2 py-1.5 text-sm" />
                  veces
                </label>
              ))}
            </div>
            <p className="text-xs text-gray-500">
              Si el técnico encuentra otra cantidad, la ajusta en campo y se te avisa en la OT.
            </p>
          </div>
        )}

        <fieldset className="border border-gray-100 rounded-lg p-4 space-y-3">
          <legend className="text-sm font-medium text-gray-700 px-1">Cuándo se hace</legend>
          <div className="flex gap-4 flex-wrap">
            {[['DATE', 'Por fecha (se repite sola)'], ['EVENT', 'Por evento (la creas tú cuando ocurre)']].map(([v, l]) => (
              <label key={v} className="flex items-center gap-2 text-sm text-gray-700">
                <input type="radio" name="trigger" value={v} checked={form.trigger === v} onChange={set('trigger')} />
                {l}
              </label>
            ))}
          </div>

          {porFecha && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <span className="block text-sm text-gray-700 mb-1">Frecuencia</span>
                <div className="flex gap-2">
                  <span className="self-center text-sm text-gray-500">Cada</span>
                  <input type="number" min="1" value={form.frequency_value} onChange={set('frequency_value')}
                    aria-label="Frecuencia" className="w-20 border border-gray-200 rounded-lg px-2 py-2 text-sm" />
                  <select value={form.frequency_unit} onChange={set('frequency_unit')} aria-label="Unidad"
                    className="flex-1 border border-gray-200 rounded-lg px-2 py-2 text-sm">
                    {FREQ_UNITS.map((u) => <option key={u.value} value={u.value}>{u.many}</option>)}
                  </select>
                </div>
              </div>
              <label className="block">
                <span className="block text-sm text-gray-700 mb-1">Primera vez</span>
                <input type="date" value={form.start_date} onChange={set('start_date')} className={input} />
              </label>
            </div>
          )}

          <div className="flex items-center gap-4 flex-wrap text-sm text-gray-700">
            <span>Repetir</span>
            <label className="flex items-center gap-2">
              <input type="radio" name="repeat" value="always" checked={form.repeat === 'always'} onChange={set('repeat')} />
              Siempre
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" name="repeat" value="times" checked={form.repeat === 'times'} onChange={set('repeat')} />
              Solo
              <input type="number" min="1" value={form.repeat_count} onChange={set('repeat_count')}
                disabled={form.repeat !== 'times'} aria-label="Número de veces"
                className="w-16 border border-gray-200 rounded-lg px-2 py-1 text-sm disabled:bg-gray-50" />
              {parseInt(form.repeat_count, 10) === 1 ? 'vez' : 'veces'}
            </label>
          </div>

          {porFecha && (
            <label className="flex items-start gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={form.fixed_schedule} onChange={set('fixed_schedule')} className="mt-0.5" />
              <span>
                Programación fija
                <span className="block text-xs text-gray-500">
                  {form.fixed_schedule
                    ? 'La siguiente se cuenta desde la fecha calculada: adelantar o aplazar una visita no corre el ciclo.'
                    : 'Sin marcar (lo normal): la siguiente se cuenta desde el día en que se hizo, como en Fracttal.'}
                </span>
              </span>
            </label>
          )}

          {proximas.length > 0 && (
            <p className="text-xs text-gray-500">
              {task ? 'Con estos datos, desde el inicio: ' : 'Primeras fechas si se hiciera cada una a tiempo: '}
              {proximas.map((f) => formatDate(f)).join(' · ')}
            </p>
          )}
        </fieldset>

        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">Descripción</span>
          <textarea value={form.description} onChange={set('description')} rows={2}
            className={`${input} resize-none`} placeholder="Opcional: instrucciones para el técnico" />
        </label>

        {!task && porFecha && plan.assets_count > 0 && (
          <p className="text-sm text-gray-600 bg-brand/5 border border-brand/10 rounded-lg px-3 py-2">
            Los {plan.assets_count} activos del plan quedan con esta tarea pendiente para el{' '}
            {formatDate(form.start_date || todayIso())}.
          </p>
        )}

        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        <div className="flex justify-end gap-3">
          <button type="button" onClick={onClose} className={btnGhost}>Cancelar</button>
          <button type="submit" disabled={saveMut.isPending} className={btnPrimary}>
            {saveMut.isPending && <Spinner />}
            {task ? 'Guardar' : 'Agregar tarea'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function ToggleTaskModal({ task, onClose }) {
  const saveMut = useSavePlanTask()
  const deleteMut = useDeletePlanTask()
  const [error, setError] = useState('')
  const desactivar = task.is_active
  const sinHistorial = task.open_count === 0 && task.done_count === 0

  async function run(fn) {
    setError('')
    try {
      await fn()
      onClose()
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  return (
    <Modal title={desactivar ? `Desactivar «${task.name}»` : `Activar «${task.name}»`} onClose={onClose} width="max-w-md">
      <div className="space-y-4 text-sm text-gray-600">
        {desactivar ? (
          <p>
            Deja de generarse en los activos del plan.
            {task.open_count > 0 && ` Sus pendientes se anulan; las que ya están dentro de una OT siguen su curso.`}
            {' '}El historial se conserva y se puede volver a activar.
          </p>
        ) : (
          <p>Cada activo del plan vuelve a tener su pendiente, contada desde la última vez que se hizo.</p>
        )}
        {error && <p className="text-red-600" role="alert">{error}</p>}
        <div className="flex justify-between gap-3 flex-wrap">
          {sinHistorial ? (
            <button onClick={() => run(() => deleteMut.mutateAsync(task.id))}
              className="text-sm text-red-600 hover:underline">
              Eliminar la tarea
            </button>
          ) : <span />}
          <div className="flex gap-3">
            <button onClick={onClose} className={btnGhost}>Cancelar</button>
            <button onClick={() => run(() => saveMut.mutateAsync({ id: task.id, is_active: !desactivar }))}
              disabled={saveMut.isPending} className={btnPrimary}>
              {saveMut.isPending && <Spinner />}
              {desactivar ? 'Desactivar' : 'Activar'}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  )
}

function EventOccurrenceModal({ plan, task, onClose }) {
  const createMut = useCreateEventOccurrence()
  const [asset, setAsset] = useState('')
  const [fecha, setFecha] = useState(todayIso())
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    try {
      await createMut.mutateAsync({ planTaskId: task.id, asset, scheduled_date: fecha })
      onClose()
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  return (
    <Modal title={`«${task.name}» en un activo`} subtitle="Queda como tarea pendiente, lista para meterla en una OT."
      onClose={onClose} width="max-w-md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">Activo *</span>
          <select value={asset} onChange={(e) => setAsset(e.target.value)} required className={input}>
            <option value="">Elige un activo del plan</option>
            {plan.assets.map((a) => <option key={a.id} value={a.id}>{a.code} — {a.name}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">Fecha *</span>
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} required className={input} />
        </label>
        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        <div className="flex justify-end gap-3">
          <button type="button" onClick={onClose} className={btnGhost}>Cancelar</button>
          <button type="submit" disabled={createMut.isPending || !asset} className={btnPrimary}>
            {createMut.isPending && <Spinner />} Crear tarea
          </button>
        </div>
      </form>
    </Modal>
  )
}

// ── Activos del plan ─────────────────────────────────────────────────────────

function AssetsTab({ plan, isAdmin }) {
  const navigate = useNavigate()
  const [assigning, setAssigning] = useState(false)
  const [removing, setRemoving] = useState(null)
  const removeMut = useRemovePlanAssets(plan.id)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <p className="text-sm text-gray-500">
          Un activo tiene un solo plan. Asignarle este le quita el que tenía, sin perder su fecha.
        </p>
        {isAdmin && (
          <button onClick={() => setAssigning(true)} className={btnPrimary}>
            <Icon name="plus" className="w-4 h-4" /> Asignar activos
          </button>
        )}
      </div>

      {plan.assets.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-10">Ningún activo tiene este plan todavía.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr className="text-left text-xs font-medium text-gray-500">
                <th className="px-3 py-2">Código</th>
                <th className="px-3 py-2">Activo</th>
                <th className="px-3 py-2">Hospital y ubicación</th>
                <th className="px-3 py-2">Próxima fecha</th>
                <th className="px-3 py-2 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {plan.assets.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs text-gray-500">{a.code}</td>
                  <td className="px-3 py-2 text-gray-800">{a.name}</td>
                  <td className="px-3 py-2 text-gray-500">
                    {a.hospital.name}
                    {a.node_path && <span className="block text-xs">{a.node_path}</span>}
                  </td>
                  <td className="px-3 py-2 text-gray-600">
                    {a.next_due_date ? formatDate(a.next_due_date) : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex justify-end gap-1">
                      <button onClick={() => navigate(`/activos/${a.id}`)}
                        className="text-xs px-2 py-1 rounded bg-brand/10 text-brand hover:bg-brand/20">
                        Ver activo
                      </button>
                      {isAdmin && (
                        <button onClick={() => setRemoving(a)}
                          className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200">
                          Quitar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {assigning && <AssignAssetsModal plan={plan} onClose={() => setAssigning(false)} />}
      {removing && (
        <Modal title={`Quitar el plan a ${removing.code}`} onClose={() => setRemoving(null)} width="max-w-md">
          <div className="space-y-4 text-sm text-gray-600">
            <p>
              {removing.name} queda sin plan de tareas. Sus pendientes de este plan se anulan; si tiene
              una tarea dentro de una OT, esa se hace igual.
            </p>
            {removeMut.isError && <p className="text-red-600">{apiErrorMessage(removeMut.error)}</p>}
            <div className="flex justify-end gap-3">
              <button onClick={() => setRemoving(null)} className={btnGhost}>Cancelar</button>
              <button disabled={removeMut.isPending} className={btnPrimary}
                onClick={() => removeMut.mutate([removing.id], { onSuccess: () => setRemoving(null) })}>
                {removeMut.isPending && <Spinner />} Quitar plan
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

function AssignAssetsModal({ plan, onClose }) {
  const fijo = plan.restrict_to_hospital?.id
  const { data: hospitals = [] } = useHospitals({ is_active: true })
  const [hospital, setHospital] = useState(fijo ?? '')
  const [node, setNode] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [soloSinPlan, setSoloSinPlan] = useState(false)
  const [selected, setSelected] = useState(() => new Set())
  const [result, setResult] = useState(null)
  const assignMut = useAssignPlanAssets(plan.id)

  const { data: tree = [] } = useAssetTree(hospital)
  const nodos = useMemo(() => flattenTree(tree), [tree])

  const params = {
    hospital_id: hospital,
    status: 'ACTIVE',
    ...(node && { node_id: node, include_sublocations: true }),
    ...(search && { search }),
    ...(soloSinPlan && { plan_id: 'none' }),
  }
  const { data: assets = [], isFetching } = useAssets(params, { enabled: !!hospital })
  const candidatos = hospital ? assets.filter((a) => a.plan?.id !== plan.id) : []
  const todosMarcados = candidatos.length > 0 && candidatos.every((a) => selected.has(a.id))
  const cambian = candidatos.filter((a) => selected.has(a.id) && a.plan)

  function toggle(id) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleTodos() {
    setSelected((prev) => {
      const next = new Set(prev)
      for (const a of candidatos) {
        if (todosMarcados) next.delete(a.id)
        else next.add(a.id)
      }
      return next
    })
  }

  async function handleAssign() {
    try {
      setResult(await assignMut.mutateAsync([...selected]))
      setSelected(new Set())
    } catch {
      // el error se muestra abajo
    }
  }

  return (
    <Modal title={`Asignar «${plan.name}»`} subtitle="Filtra por hospital y ubicación, y marca los activos."
      onClose={onClose} width="max-w-3xl">
      <div className="space-y-4">
        {result && (
          <div className="text-sm bg-green-50 border border-green-100 rounded-lg px-3 py-2 text-green-800 space-y-1" role="status">
            <p className="flex items-center gap-1.5">
              <Icon name="checkCircle" className="w-4 h-4" />
              Plan asignado a {result.assigned} activo{result.assigned !== 1 ? 's' : ''}.
            </p>
            {result.moved.length > 0 && (
              <p className="text-xs">
                Cambiaron de plan:{' '}
                {result.moved.map((m) => (
                  `${m.code} (antes «${m.from_plan}»${m.kept_date ? `; conserva su fecha, ${formatDate(m.kept_date)}` : ''})`
                )).join(', ')}.
              </p>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label className="block">
            <span className="block text-sm font-medium text-gray-700 mb-1">Hospital</span>
            <select value={hospital} disabled={!!fijo} className={input}
              onChange={(e) => { setHospital(e.target.value); setNode(''); setSelected(new Set()) }}>
              <option value="">Elige un hospital</option>
              {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="block text-sm font-medium text-gray-700 mb-1">Ubicación (incluye lo que tiene dentro)</span>
            <select value={node} onChange={(e) => setNode(e.target.value)} disabled={!hospital} className={input}>
              <option value="">Todo el hospital</option>
              {nodos.map((n) => <option key={n.id} value={n.id}>{indentedLabel(n.name, n.depth)}</option>)}
            </select>
          </label>
        </div>
        <div className="flex gap-3 flex-wrap items-center">
          <form onSubmit={(e) => { e.preventDefault(); setSearch(searchInput.trim()) }} className="flex gap-2 flex-1 min-w-[16rem]">
            <input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} disabled={!hospital}
              placeholder="Código o nombre" aria-label="Buscar activo" className={input} />
            <button type="submit" disabled={!hospital}
              className="px-3 py-2 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">Buscar</button>
          </form>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={soloSinPlan} onChange={(e) => setSoloSinPlan(e.target.checked)} />
            Solo activos sin plan
          </label>
        </div>

        <div className="border border-gray-100 rounded-lg max-h-80 overflow-y-auto">
          {!hospital ? (
            <p className="text-sm text-gray-500 text-center py-8">Elige un hospital para ver sus activos.</p>
          ) : isFetching && assets.length === 0 ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : candidatos.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">No hay activos para asignar con este filtro.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr className="text-left text-xs font-medium text-gray-500">
                  <th className="px-3 py-2 w-8">
                    <input type="checkbox" checked={todosMarcados} onChange={toggleTodos} aria-label="Marcar todos" />
                  </th>
                  <th className="px-3 py-2">Activo</th>
                  <th className="px-3 py-2">Ubicación</th>
                  <th className="px-3 py-2">Plan actual</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {candidatos.map((a) => (
                  <tr key={a.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => toggle(a.id)}>
                    <td className="px-3 py-2">
                      <input type="checkbox" checked={selected.has(a.id)} onChange={() => toggle(a.id)}
                        onClick={(e) => e.stopPropagation()} aria-label={`Marcar ${a.code}`} />
                    </td>
                    <td className="px-3 py-2">
                      <span className="font-mono text-xs text-gray-500">{a.code}</span>{' '}
                      <span className="text-gray-800">{a.name}</span>
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-500">{a.node?.path ?? '—'}</td>
                    <td className="px-3 py-2 text-xs">
                      {a.plan ? <span className="text-amber-700">{a.plan.name}</span> : <span className="text-gray-400">Sin plan</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {cambian.length > 0 && (
          <p className="text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
            {cambian.length} de los marcados ya tienen otro plan: se cambian a este. Si tenían una tarea
            pendiente, la nueva conserva su fecha.
          </p>
        )}
        {assignMut.isError && <p className="text-sm text-red-600" role="alert">{apiErrorMessage(assignMut.error)}</p>}

        <div className="flex justify-end gap-3">
          <button onClick={onClose} className={btnGhost}>{result ? 'Cerrar' : 'Cancelar'}</button>
          <button onClick={handleAssign} disabled={selected.size === 0 || assignMut.isPending} className={btnPrimary}>
            {assignMut.isPending && <Spinner />}
            Asignar a {selected.size} activo{selected.size !== 1 ? 's' : ''}
          </button>
        </div>
      </div>
    </Modal>
  )
}

// ── Cumplimiento ─────────────────────────────────────────────────────────────

const MONTHS_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

function ComplianceTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-3 text-xs">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      <p>Programadas: {d.total}</p>
      <p>Hechas: {d.completed}</p>
      <p>Cumplimiento: {d.hasData ? `${d.pct}%` : 'Sin datos'}</p>
    </div>
  )
}

function ComplianceTab({ planId }) {
  const { data, isLoading } = useComplianceData(planId)

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>
  if (!data) return null

  const chartData = (data.monthly ?? []).map((m) => ({
    name: `${MONTHS_ES[m.month - 1]} ${String(m.year).slice(2)}`,
    pct: m.percentage ?? 0,
    total: m.total,
    completed: m.completed,
    hasData: m.total > 0,
  }))

  function barColor(pct, hasData) {
    if (!hasData) return '#e5e7eb'
    if (pct >= 80) return '#22c55e'
    if (pct >= 50) return '#facc15'
    return '#ef4444'
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-600 mb-1">Cumplimiento de los últimos 12 meses</h3>
      <p className="text-xs text-gray-500 mb-4">Tareas del plan programadas en cada mes y cuántas se hicieron.</p>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
          <Tooltip content={<ComplianceTooltip />} />
          <Bar dataKey="pct" radius={[3, 3, 0, 0]}>
            {chartData.map((entry, i) => <Cell key={i} fill={barColor(entry.pct, entry.hasData)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
