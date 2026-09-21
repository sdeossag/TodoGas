import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAssetTree, useHospitals } from '../../api/assets'
import { useMaintenancePlans } from '../../api/maintenance'
import {
  useCancelTasks,
  useCreateWorkOrderFromTasks,
  useRescheduleCauses,
  useRescheduleTasks,
  useTaskReschedules,
  useTasks,
} from '../../api/tasks'
import { useUsers } from '../../api/users'
import Icon from '../../components/ui/Icon'
import Modal from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import { taskTypeLabel } from '../../constants/labels'
import { apiErrorMessage } from '../../utils/apiError'
import { formatWoCode } from '../../utils/workOrder'
import { commonAncestor, flattenTree, indentedLabel, parentMap } from '../../utils/locationTree'
import {
  PRIORITIES,
  durationMinutes,
  formatDate,
  formatDuration,
  formatFrequency,
  formatMinutes,
  relativeDue,
  todayIso,
} from '../../utils/maintenance'

const btnPrimary = 'px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60 flex items-center gap-2'
const btnGhost = 'px-4 py-2 text-sm text-gray-600 hover:text-gray-800'
const input = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30'
const PESO = { HIGH: 0, MEDIUM: 1, LOW: 2 }

/**
 * Tareas pendientes: el centro del trabajo del planificador, como la primera
 * columna del kanban de Fracttal. Se filtran por hospital y ubicación, se
 * marcan las de una misma visita y se arma la OT, o se reprograman con causa.
 */
export default function PendingTasksPage() {
  const [hospital, setHospital] = useState('')
  const [node, setNode] = useState('')
  const [plan, setPlan] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [soloVencidas, setSoloVencidas] = useState(false)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(() => new Set())
  const [modal, setModal] = useState(null) // 'ot' | 'reprogramar' | 'anular'
  const [historyTask, setHistoryTask] = useState(null)
  const [flash, setFlash] = useState('')

  const { data: hospitals = [] } = useHospitals({ is_active: true })
  const { data: plans = [] } = useMaintenancePlans({ is_active: true })
  const { data: tree = [] } = useAssetTree(hospital)
  const nodos = useMemo(() => flattenTree(tree), [tree])

  const params = {
    status: 'PENDING',
    ...(hospital && { hospital_id: hospital }),
    ...(node && { node_id: node }),
    ...(plan && { plan_id: plan }),
    ...(desde && { due_after: desde }),
    ...(hasta && { due_before: hasta }),
    ...(soloVencidas && { overdue: true }),
    ...(search && { search }),
  }
  const { data: tareas = [], isLoading, isError } = useTasks(params)

  // Una selección escondida por un filtro terminaría dentro de una OT sin que
  // el planificador la viera: al cambiar el filtro se empieza de cero.
  const filtros = JSON.stringify(params)
  useEffect(() => { setSelected(new Set()) }, [filtros])

  const marcadas = tareas.filter((t) => selected.has(t.id))
  const hospitalesMarcados = [...new Set(marcadas.map((t) => t.hospital.name))]
  const minutos = marcadas.reduce((acc, t) => acc + durationMinutes(t.estimated_duration), 0)
  const vencidas = tareas.filter((t) => t.is_overdue).length
  const todas = tareas.length > 0 && tareas.every((t) => selected.has(t.id))

  function toggle(id) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function terminar(mensaje) {
    setModal(null)
    setSelected(new Set())
    setFlash(mensaje)
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Tareas pendientes</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Marca las de una misma visita y crea la OT, o reprográmalas indicando la causa.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-card p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <label className="block">
          <span className="block text-xs font-medium text-gray-500 mb-1">Hospital</span>
          <select value={hospital} onChange={(e) => { setHospital(e.target.value); setNode('') }} className={input}>
            <option value="">Todos</option>
            {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="block text-xs font-medium text-gray-500 mb-1">Ubicación (con lo que tiene dentro)</span>
          <select value={node} onChange={(e) => setNode(e.target.value)} disabled={!hospital} className={input}>
            <option value="">{hospital ? 'Todo el hospital' : 'Elige primero el hospital'}</option>
            {nodos.map((n) => <option key={n.id} value={n.id}>{indentedLabel(n.name, n.depth)}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="block text-xs font-medium text-gray-500 mb-1">Plan de tareas</span>
          <select value={plan} onChange={(e) => setPlan(e.target.value)} className={input}>
            <option value="">Todos</option>
            {plans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </label>
        <form onSubmit={(e) => { e.preventDefault(); setSearch(searchInput.trim()) }} className="block">
          <span className="block text-xs font-medium text-gray-500 mb-1">Activo o tarea</span>
          <div className="flex gap-2">
            <input value={searchInput} onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Código, nombre…" aria-label="Buscar activo o tarea" className={input} />
            <button type="submit" aria-label="Buscar" className="px-3 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">
              <Icon name="search" className="w-4 h-4" />
            </button>
          </div>
        </form>
        <label className="block">
          <span className="block text-xs font-medium text-gray-500 mb-1">Desde</span>
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className={input} />
        </label>
        <label className="block">
          <span className="block text-xs font-medium text-gray-500 mb-1">Hasta</span>
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className={input} />
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-700 sm:self-end sm:pb-2">
          <input type="checkbox" checked={soloVencidas} onChange={(e) => setSoloVencidas(e.target.checked)} />
          Solo vencidas
        </label>
      </div>

      {flash && (
        <div className="flex items-start justify-between gap-3 text-sm bg-green-50 border border-green-100 text-green-800 rounded-lg px-3 py-2" role="status">
          <span className="flex items-center gap-1.5"><Icon name="checkCircle" className="w-4 h-4 flex-shrink-0" />{flash}</span>
          <button onClick={() => setFlash('')} aria-label="Cerrar aviso" className="text-green-700 text-lg leading-none">&times;</button>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        <div className="px-4 py-3 border-b flex items-center gap-3 flex-wrap min-h-[3.5rem]">
          {marcadas.length === 0 ? (
            <p className="text-sm text-gray-500">
              {tareas.length} pendiente{tareas.length !== 1 ? 's' : ''}
              {vencidas > 0 && <span className="text-red-700"> · {vencidas} vencida{vencidas !== 1 ? 's' : ''}</span>}
            </p>
          ) : (
            <>
              <p className="text-sm text-gray-800 font-medium">
                {marcadas.length} marcada{marcadas.length !== 1 ? 's' : ''}
                <span className="font-normal text-gray-500">{minutos > 0 && ` · ${formatMinutes(minutos)} en total`} · {hospitalesMarcados.join(', ')}</span>
              </p>
              <div className="flex gap-2 ml-auto flex-wrap">
                <button onClick={() => setModal('ot')} disabled={hospitalesMarcados.length > 1}
                  title={hospitalesMarcados.length > 1 ? 'Una OT es de un solo hospital' : undefined}
                  className={btnPrimary}>
                  <Icon name="workOrder" className="w-4 h-4" /> Crear OT
                </button>
                <button onClick={() => setModal('reprogramar')}
                  className="px-4 py-2 text-sm rounded-lg bg-amber-50 text-amber-800 hover:bg-amber-100">
                  Reprogramar
                </button>
                <button onClick={() => setModal('anular')}
                  className="px-4 py-2 text-sm rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200">
                  Anular
                </button>
                <button onClick={() => setSelected(new Set())} className="px-2 py-2 text-sm text-gray-500 hover:text-gray-700">
                  Desmarcar
                </button>
              </div>
              {hospitalesMarcados.length > 1 && (
                <p className="w-full text-xs text-amber-700">Para crear una OT marca tareas de un solo hospital.</p>
              )}
            </>
          )}
        </div>

        {isError ? (
          <p className="text-center py-16 text-red-600 text-sm">No se pudieron cargar las tareas. Revisa tu conexión e intenta de nuevo.</p>
        ) : isLoading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : tareas.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <Icon name="checkCircle" className="w-10 h-10 mx-auto mb-3 text-gray-400" />
            <p className="font-medium">No hay tareas pendientes con este filtro</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr className="text-left text-xs font-medium text-gray-500">
                  <th className="px-4 py-3 w-8">
                    <input type="checkbox" checked={todas} aria-label="Marcar todas"
                      onChange={() => setSelected(todas ? new Set() : new Set(tareas.map((t) => t.id)))} />
                  </th>
                  <th className="px-4 py-3">Fecha programada</th>
                  <th className="px-4 py-3">Activo</th>
                  <th className="px-4 py-3">Tarea</th>
                  <th className="px-4 py-3">Cuándo</th>
                  <th className="px-4 py-3">Duración</th>
                  <th className="px-4 py-3"><span className="sr-only">Historial</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {tareas.map((t) => (
                  <tr key={t.id} onClick={() => toggle(t.id)}
                    className={`cursor-pointer align-top ${selected.has(t.id) ? 'bg-brand/5' : 'hover:bg-gray-50'}`}>
                    <td className="px-4 py-3">
                      <input type="checkbox" checked={selected.has(t.id)} onChange={() => toggle(t.id)}
                        onClick={(e) => e.stopPropagation()} aria-label={`Marcar ${t.asset.code}`} />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {/* text-wrap: pretty de los <p> (index.css) anula el nowrap heredado. */}
                      <p className={`whitespace-nowrap ${t.is_overdue ? 'text-red-700 font-medium' : 'text-gray-800'}`}>{formatDate(t.scheduled_date)}</p>
                      <p className={`text-xs whitespace-nowrap ${t.is_overdue ? 'text-red-600' : 'text-gray-500'}`}>
                        {t.is_overdue ? `vencida ${relativeDue(t.scheduled_date)}` : relativeDue(t.scheduled_date)}
                      </p>
                      {t.is_rescheduled && (
                        <p className="text-xs text-amber-700 whitespace-nowrap" title="Fecha calculada por la frecuencia">
                          Reprogramada · calc. {formatDate(t.calculated_date, { day: '2-digit', month: 'short' })}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Link to={`/activos/${t.asset.id}`} onClick={(e) => e.stopPropagation()}
                        className="text-gray-800 hover:text-brand">
                        <span className="font-mono text-xs text-gray-500">{t.asset.code}</span> {t.asset.name}
                      </Link>
                      <p className="text-xs text-gray-500">
                        {t.hospital.name}{t.asset.node_path && ` · ${t.asset.node_path}`}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-gray-800">{t.title}</p>
                      <p className="text-xs text-gray-500">{taskTypeLabel(t.task_type)}{t.plan && ` · ${t.plan.name}`}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{formatFrequency(t.plan_task)}</td>
                    <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{formatDuration(t.estimated_duration)}</td>
                    <td className="px-4 py-3">
                      <button onClick={(e) => { e.stopPropagation(); setHistoryTask(t) }}
                        aria-label={`Historial de ${t.asset.code}`} title="Fechas e historial de reprogramaciones"
                        className="p-1 rounded text-gray-500 hover:text-brand hover:bg-gray-100">
                        <Icon name="clock" className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modal === 'ot' && <CreateWorkOrderModal tasks={marcadas} onClose={() => setModal(null)} />}
      {modal === 'reprogramar' && (
        <RescheduleModal tasks={marcadas} onClose={() => setModal(null)}
          onDone={(n) => terminar(n === 0
            ? 'Ninguna cambió: ya tenían esa fecha.'
            : `${n} tarea${n !== 1 ? 's' : ''} reprogramada${n !== 1 ? 's' : ''}.`)} />
      )}
      {modal === 'anular' && (
        <CancelModal tasks={marcadas} onClose={() => setModal(null)}
          onDone={(n) => terminar(`${n} tarea${n !== 1 ? 's' : ''} anulada${n !== 1 ? 's' : ''}.`)} />
      )}
      {historyTask && <HistoryModal task={historyTask} onClose={() => setHistoryTask(null)} />}
    </div>
  )
}

// ── Crear OT ─────────────────────────────────────────────────────────────────

function proposedTitle(tasks, locationName) {
  if (tasks.length === 1) {
    const t = tasks[0]
    return `${t.plan ? '[PM] ' : ''}${t.title} — ${t.asset.name}`
  }
  const tipos = new Set(tasks.map((t) => t.task_type))
  const tipo = tipos.size === 1 ? taskTypeLabel(tasks[0].task_type) : 'Mantenimiento'
  return `${tipo} — ${tasks.length} activos${locationName ? ` — ${locationName}` : ''}`
}

// Los modales guardan la selección con la que se abrieron: al terminar, la
// lista se recarga y esas tareas dejan de estar pendientes (o cambian), y el
// modal no puede quedarse sin ellas mientras muestra el resultado.

function CreateWorkOrderModal({ tasks: seleccion, onClose }) {
  const [tasks] = useState(seleccion)
  const navigate = useNavigate()
  const hospital = tasks[0].hospital
  const createMut = useCreateWorkOrderFromTasks()
  const tecnicos = (useUsers({}).data ?? []).filter((u) => u.role === 'TEC' && u.is_active)
  const { data: tree = [] } = useAssetTree(hospital.id)
  const nodos = useMemo(() => flattenTree(tree), [tree])
  const comun = useMemo(
    () => commonAncestor(tasks.map((t) => t.asset.node_id), parentMap(tree)),
    [tasks, tree],
  )

  const primera = tasks.map((t) => t.scheduled_date).sort()[0]
  const [form, setForm] = useState({
    assigned_to: '',
    scheduled_date: primera < todayIso() ? todayIso() : primera,
    priority: [...tasks].sort((a, b) => (PESO[a.priority] ?? 9) - (PESO[b.priority] ?? 9))[0].priority,
    location: '',
    title: '',
    description: '',
  })
  const [tocado, setTocado] = useState({ location: false, title: false })
  const [error, setError] = useState('')
  const [creada, setCreada] = useState(null)

  // La ubicación común llega cuando carga el árbol; no pisa una elegida a mano.
  useEffect(() => {
    if (!tocado.location && comun) setForm((f) => ({ ...f, location: comun }))
  }, [comun, tocado.location])

  const nombreUbicacion = nodos.find((n) => n.id === form.location)?.name
  const titulo = tocado.title ? form.title : proposedTitle(tasks, nombreUbicacion)
  const minutos = tasks.reduce((acc, t) => acc + durationMinutes(t.estimated_duration), 0)

  const set = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }))
    if (field in tocado) setTocado((t) => ({ ...t, [field]: true }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    try {
      const ot = await createMut.mutateAsync({
        task_ids: tasks.map((t) => t.id),
        title: titulo.trim(),
        description: form.description.trim(),
        scheduled_date: form.scheduled_date,
        priority: form.priority,
        assigned_to: form.assigned_to || null,
        location: form.location || null,
      })
      setCreada(ot)
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo crear la OT.'))
    }
  }

  if (creada) {
    return (
      <Modal title="OT creada" onClose={onClose} width="max-w-md">
        <div className="space-y-4 text-sm">
          <p className="text-gray-700 flex items-center gap-2">
            <Icon name="checkCircle" className="w-5 h-5 text-green-600" />
            {formatWoCode(creada) || 'La OT'} quedó con {tasks.length} tarea{tasks.length !== 1 ? 's' : ''}.
          </p>
          {creada.warnings?.map((w) => (
            <p key={w} className="text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2 flex gap-1.5">
              <Icon name="warning" className="w-4 h-4 flex-shrink-0" />{w}
            </p>
          ))}
          <div className="flex justify-end gap-3">
            <button onClick={onClose} className={btnGhost}>Seguir planificando</button>
            <button onClick={() => navigate(`/ordenes/${creada.id}`)} className={btnPrimary}>Ver la OT</button>
          </div>
        </div>
      </Modal>
    )
  }

  return (
    <Modal title="Crear OT" subtitle={`${hospital.name} · ${tasks.length} tarea${tasks.length !== 1 ? 's' : ''}${minutos ? ` · ${formatMinutes(minutos)}` : ''}`}
      onClose={onClose} width="max-w-2xl">
      <form onSubmit={handleSubmit} className="space-y-4">
        <ul className="border border-gray-100 rounded-lg divide-y divide-gray-50 max-h-40 overflow-y-auto text-sm">
          {tasks.map((t) => (
            <li key={t.id} className="px-3 py-2 flex justify-between gap-3">
              <span className="text-gray-800 min-w-0 truncate">
                <span className="font-mono text-xs text-gray-500">{t.asset.code}</span> {t.asset.name} · {t.title}
              </span>
              <span className="text-xs text-gray-500 whitespace-nowrap">{formatDate(t.scheduled_date)}</span>
            </li>
          ))}
        </ul>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <label className="block">
            <span className="block text-sm font-medium text-gray-700 mb-1">Técnico</span>
            <select value={form.assigned_to} onChange={set('assigned_to')} className={input}>
              <option value="">Sin asignar</option>
              {tecnicos.map((u) => <option key={u.id} value={u.id}>{`${u.first_name} ${u.last_name}`.trim() || u.email}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="block text-sm font-medium text-gray-700 mb-1">Fecha de la visita</span>
            <input type="date" value={form.scheduled_date} onChange={set('scheduled_date')} required className={input} />
          </label>
          <label className="block">
            <span className="block text-sm font-medium text-gray-700 mb-1">Prioridad</span>
            <select value={form.priority} onChange={set('priority')} className={input}>
              {PRIORITIES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </label>
        </div>

        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">Ubicación de la visita</span>
          <select value={form.location} onChange={set('location')} className={input}>
            <option value="">Sin ubicación</option>
            {nodos.map((n) => <option key={n.id} value={n.id}>{indentedLabel(n.name, n.depth)}</option>)}
          </select>
          {comun && form.location === comun && (
            <span className="block text-xs text-gray-500 mt-1">Propuesta: es la ubicación que comparten todas las tareas.</span>
          )}
        </label>

        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">Título</span>
          <input value={titulo} onChange={set('title')} required maxLength={500} className={input} />
        </label>

        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">Indicaciones para el técnico</span>
          <textarea value={form.description} onChange={set('description')} rows={2}
            className={`${input} resize-none`} placeholder="Opcional" />
        </label>

        {form.scheduled_date !== primera && (
          <p className="text-xs text-gray-500">
            La fecha de la visita no cambia la fecha programada de cada tarea. Si una se hace en otra fecha por
            una causa (por ejemplo, NO DISPONIBLE), reprográmala antes para que quede registrado.
          </p>
        )}

        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        <div className="flex justify-end gap-3">
          <button type="button" onClick={onClose} className={btnGhost}>Cancelar</button>
          <button type="submit" disabled={createMut.isPending} className={btnPrimary}>
            {createMut.isPending && <Spinner />} Crear OT
          </button>
        </div>
      </form>
    </Modal>
  )
}

// ── Reprogramar y anular ─────────────────────────────────────────────────────

function RescheduleModal({ tasks: seleccion, onClose, onDone }) {
  const [tasks] = useState(seleccion)
  const { data: causas = [] } = useRescheduleCauses()
  const mut = useRescheduleTasks()
  const [fecha, setFecha] = useState('')
  const [causa, setCausa] = useState('')
  const [nota, setNota] = useState('')
  const [error, setError] = useState('')
  const una = tasks.length === 1 ? tasks[0] : null

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    try {
      const res = await mut.mutateAsync({
        task_ids: tasks.map((t) => t.id), scheduled_date: fecha, cause_id: causa, note: nota.trim(),
      })
      onDone(res.rescheduled)
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo reprogramar.'))
    }
  }

  return (
    <Modal title={una ? `Reprogramar ${una.asset.code}` : `Reprogramar ${tasks.length} tareas`}
      subtitle={una ? `${una.title} · programada para el ${formatDate(una.scheduled_date)}` : undefined}
      onClose={onClose} width="max-w-md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">Nueva fecha *</span>
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} required autoFocus className={input} />
        </label>
        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">Causa *</span>
          <select value={causa} onChange={(e) => setCausa(e.target.value)} required className={input}>
            <option value="">Elige la causa</option>
            {causas.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">Nota</span>
          <textarea value={nota} onChange={(e) => setNota(e.target.value)} rows={2}
            className={`${input} resize-none`} placeholder="Opcional: quién lo pidió, qué pasó" />
        </label>
        <p className="text-xs text-gray-500">
          Cambia la fecha programada; la calculada se conserva y queda registrado quién, cuándo y por qué.
        </p>
        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        <div className="flex justify-end gap-3">
          <button type="button" onClick={onClose} className={btnGhost}>Cancelar</button>
          <button type="submit" disabled={mut.isPending} className={btnPrimary}>
            {mut.isPending && <Spinner />} Reprogramar
          </button>
        </div>
      </form>
    </Modal>
  )
}

function CancelModal({ tasks: seleccion, onClose, onDone }) {
  const [tasks] = useState(seleccion)
  const mut = useCancelTasks()
  const [nota, setNota] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    try {
      const res = await mut.mutateAsync({ task_ids: tasks.map((t) => t.id), note: nota.trim() })
      onDone(res.cancelled)
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo anular.'))
    }
  }

  return (
    <Modal title={tasks.length === 1 ? `Anular la tarea de ${tasks[0].asset.code}` : `Anular ${tasks.length} tareas`}
      onClose={onClose} width="max-w-md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <p className="text-sm text-gray-600">
          Anular es decir «esta ya no toca»: no se hace ni se crea la siguiente. Si lo que pasa es que se hará
          otro día, mejor reprográmala.
        </p>
        <label className="block">
          <span className="block text-sm font-medium text-gray-700 mb-1">Por qué se anula *</span>
          <textarea value={nota} onChange={(e) => setNota(e.target.value)} rows={3} required autoFocus
            className={`${input} resize-none`} placeholder="Ej: el equipo se retiró del servicio" />
        </label>
        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        <div className="flex justify-end gap-3">
          <button type="button" onClick={onClose} className={btnGhost}>Cancelar</button>
          <button type="submit" disabled={mut.isPending || !nota.trim()}
            className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-60 flex items-center gap-2">
            {mut.isPending && <Spinner />} Anular
          </button>
        </div>
      </form>
    </Modal>
  )
}

function HistoryModal({ task, onClose }) {
  const { data: registros = [], isLoading } = useTaskReschedules(task.id)

  return (
    <Modal title={`${task.asset.code} · ${task.title}`} subtitle={task.plan?.name} onClose={onClose}>
      <div className="space-y-4 text-sm">
        <dl className="grid grid-cols-2 gap-3">
          <div>
            <dt className="text-xs text-gray-500">Fecha calculada</dt>
            <dd className="text-gray-800">{formatDate(task.calculated_date)}</dd>
          </div>
          <div>
            <dt className="text-xs text-gray-500">Fecha programada</dt>
            <dd className="text-gray-800">{formatDate(task.scheduled_date)}</dd>
          </div>
        </dl>
        <div>
          <h3 className="text-xs font-medium text-gray-500 mb-2">Reprogramaciones</h3>
          {isLoading ? (
            <Spinner />
          ) : registros.length === 0 ? (
            <p className="text-gray-500">Nunca se ha reprogramado.</p>
          ) : (
            <ol className="space-y-2">
              {registros.map((r) => (
                <li key={r.id} className="border border-gray-100 rounded-lg px-3 py-2">
                  <p className="text-gray-800">
                    {formatDate(r.from_date)} → {formatDate(r.to_date)} · <span className="font-medium">{r.cause}</span>
                  </p>
                  {r.note && <p className="text-gray-600">{r.note}</p>}
                  <p className="text-xs text-gray-500">
                    {r.changed_by?.full_name ?? 'Sistema'} · {new Date(r.changed_at).toLocaleString('es-CO')}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </Modal>
  )
}
