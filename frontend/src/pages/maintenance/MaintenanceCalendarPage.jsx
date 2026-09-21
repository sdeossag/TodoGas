import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useHospitals } from '../../api/assets'
import { useTasks } from '../../api/tasks'
import Icon from '../../components/ui/Icon'
import Spinner from '../../components/ui/Spinner'
import { formatDate } from '../../utils/maintenance'

const DAYS_OF_WEEK = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
const MONTHS_ES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

// Un color por situación de la tarea, en el orden en que importa verlas.
const KINDS = {
  overdue: { label: 'Vencida', dot: 'bg-red-500', badge: 'bg-red-50 text-red-700' },
  rescheduled: { label: 'Reprogramada', dot: 'bg-amber-400', badge: 'bg-amber-50 text-amber-800' },
  pending: { label: 'Pendiente', dot: 'bg-gray-400', badge: 'bg-gray-100 text-gray-700' },
  scheduled: { label: 'En OT', dot: 'bg-blue-500', badge: 'bg-blue-50 text-blue-700' },
  done: { label: 'Finalizada', dot: 'bg-green-500', badge: 'bg-green-50 text-green-700' },
}

function kindOf(task) {
  if (task.status === 'DONE') return 'done'
  if (task.is_overdue) return 'overdue'
  if (task.status === 'SCHEDULED') return 'scheduled'
  return task.is_rescheduled ? 'rescheduled' : 'pending'
}

function pad(n) {
  return String(n).padStart(2, '0')
}

function isoDate(y, m, d) {
  return `${y}-${pad(m + 1)}-${pad(d)}`
}

/**
 * Calendario de mantenimiento: las tareas por su fecha programada. La tarea
 * pendiente de cada activo es el calendario; no hay otra tabla.
 */
export default function MaintenanceCalendarPage() {
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())
  const [hospitalFilter, setHospitalFilter] = useState('')
  const [selectedDay, setSelectedDay] = useState(null)

  const { data: hospitals = [] } = useHospitals({ is_active: true })

  const lastDay = new Date(year, month + 1, 0).getDate()
  const { data: tasks = [], isLoading } = useTasks({
    status: 'PENDING,SCHEDULED,DONE',
    due_after: isoDate(year, month, 1),
    due_before: isoDate(year, month, lastDay),
    ...(hospitalFilter && { hospital_id: hospitalFilter }),
  })

  const byDate = useMemo(() => {
    const map = {}
    for (const t of tasks) (map[t.scheduled_date] ??= []).push(t)
    return map
  }, [tasks])

  const startOffset = new Date(year, month, 1).getDay()
  const cells = []
  for (let i = 0; i < startOffset; i++) cells.push(null)
  for (let d = 1; d <= lastDay; d++) cells.push(d)
  while (cells.length % 7 !== 0) cells.push(null)

  function moveMonth(delta) {
    const d = new Date(year, month + delta, 1)
    setYear(d.getFullYear())
    setMonth(d.getMonth())
    setSelectedDay(null)
  }

  const selectedKey = selectedDay ? isoDate(year, month, selectedDay) : null
  const selectedTasks = selectedKey ? (byDate[selectedKey] ?? []) : []
  const isToday = (d) => d === today.getDate() && month === today.getMonth() && year === today.getFullYear()

  return (
    <div className="space-y-4 max-w-6xl">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Calendario de mantenimiento</h1>
          <p className="text-sm text-gray-500 mt-0.5">Tareas por su fecha programada</p>
        </div>
        <select value={hospitalFilter} aria-label="Hospital"
          onChange={(e) => { setHospitalFilter(e.target.value); setSelectedDay(null) }}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none">
          <option value="">Todos los hospitales</option>
          {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
      </div>

      <div className="flex gap-4 flex-col lg:flex-row">
        <div className="flex-1 bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <button onClick={() => moveMonth(-1)} aria-label="Mes anterior"
              className="text-gray-500 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-50">
              <Icon name="chevronLeft" className="w-4 h-4" />
            </button>
            <h2 className="text-base font-semibold text-gray-800 flex items-center gap-2">
              {MONTHS_ES[month]} {year}
              {isLoading && <Spinner />}
            </h2>
            <button onClick={() => moveMonth(1)} aria-label="Mes siguiente"
              className="text-gray-500 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-50">
              <Icon name="chevronRight" className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-7">
            {DAYS_OF_WEEK.map((d) => (
              <div key={d} className="text-center text-xs text-gray-500 font-medium py-2 border-b">{d}</div>
            ))}
            {cells.map((day, i) => {
              if (!day) return <div key={`e-${i}`} className="min-h-[80px] bg-gray-50/50" />
              const dayTasks = byDate[isoDate(year, month, day)] ?? []
              const counts = {}
              for (const t of dayTasks) counts[kindOf(t)] = (counts[kindOf(t)] ?? 0) + 1
              return (
                <button key={day} type="button" onClick={() => setSelectedDay(day === selectedDay ? null : day)}
                  aria-label={`${day} de ${MONTHS_ES[month].toLowerCase()}: ${dayTasks.length} tareas`}
                  className={`min-h-[80px] p-1.5 border-b border-r border-gray-50 text-left transition-colors ${
                    day === selectedDay ? 'bg-brand/10' : 'hover:bg-gray-50'
                  }`}>
                  <span className={`text-xs font-medium w-6 h-6 flex items-center justify-center rounded-full ${
                    isToday(day) ? 'bg-brand text-white' : 'text-gray-600'
                  }`}>
                    {day}
                  </span>
                  {dayTasks.length > 0 && (
                    <span className="mt-1 flex flex-col gap-0.5">
                      {Object.keys(KINDS).filter((k) => counts[k]).map((k) => (
                        <span key={k} className="flex items-center gap-1 text-[11px] text-gray-600 leading-tight">
                          <span className={`w-2 h-2 rounded-full ${KINDS[k].dot}`} />{counts[k]}
                        </span>
                      ))}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        <div className="lg:w-80 flex-shrink-0 bg-white rounded-xl border border-gray-200 shadow-card">
          {!selectedDay ? (
            <div className="flex flex-col items-center justify-center h-full py-12 text-gray-500">
              <Icon name="calendar" className="w-9 h-9 mx-auto mb-2 text-gray-400" />
              <p className="text-sm text-center px-4">Elige un día para ver sus tareas</p>
            </div>
          ) : (
            <div className="p-4 space-y-3">
              <h3 className="font-semibold text-gray-800 text-sm">{selectedDay} de {MONTHS_ES[month].toLowerCase()}</h3>
              {selectedTasks.length === 0 ? (
                <p className="text-sm text-gray-500">Sin tareas este día</p>
              ) : (
                <ul className="space-y-2 max-h-[28rem] overflow-y-auto">
                  {selectedTasks.map((t) => {
                    const kind = KINDS[kindOf(t)]
                    return (
                      <li key={t.id} className="border border-gray-100 rounded-lg p-3 space-y-1">
                        <div className="flex items-center justify-between gap-2">
                          <Link to={`/activos/${t.asset.id}`} className="text-xs font-mono text-gray-500 hover:text-brand">
                            {t.asset.code}
                          </Link>
                          <span className={`text-xs px-1.5 py-0.5 rounded-full ${kind.badge}`}>{kind.label}</span>
                        </div>
                        <p className="text-sm text-gray-800">{t.asset.name}</p>
                        <p className="text-xs text-gray-500">{t.title}{t.plan && ` · ${t.plan.name}`}</p>
                        <p className="text-xs text-gray-500">{t.hospital.name}{t.asset.node_path && ` · ${t.asset.node_path}`}</p>
                        {t.is_rescheduled && (
                          <p className="text-xs text-amber-700">Fecha calculada: {formatDate(t.calculated_date)}</p>
                        )}
                        {t.work_order && (
                          <Link to={`/ordenes/${t.work_order.id}`} className="text-xs text-brand hover:underline">
                            {t.work_order.wo_code}
                          </Link>
                        )}
                      </li>
                    )
                  })}
                </ul>
              )}
              {selectedTasks.some((t) => t.status === 'PENDING') && (
                <Link to="/tareas-pendientes" className="block text-xs text-brand hover:underline">
                  Planificar en Tareas pendientes
                </Link>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="flex gap-4 flex-wrap text-xs text-gray-500">
        {Object.values(KINDS).map((k) => (
          <span key={k.label} className="flex items-center gap-1">
            <span className={`inline-block w-2 h-2 rounded-full ${k.dot}`} />{k.label}
          </span>
        ))}
      </div>
    </div>
  )
}
