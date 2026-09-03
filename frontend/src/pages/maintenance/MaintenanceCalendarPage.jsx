import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkOrders } from '../../api/workOrders'
import { useHospitals } from '../../api/assets'
import Icon from '../../components/ui/Icon'
import { woStatusLabel } from '../../constants/labels'
import { formatWoCode } from '../../utils/workOrder'

const DAYS_OF_WEEK = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
const MONTHS_ES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

function padDate(n) {
  return String(n).padStart(2, '0')
}

function isoDate(y, m, d) {
  return `${y}-${padDate(m + 1)}-${padDate(d)}`
}

export default function MaintenanceCalendarPage() {
  const navigate = useNavigate()
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())
  const [hospitalFilter, setHospitalFilter] = useState('')
  const [selectedDay, setSelectedDay] = useState(null)

  const { data: hospitals = [] } = useHospitals({ is_active: true })

  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)

  const woParams = {
    task_type: 'PREVENTIVE',
    scheduled_date_from: isoDate(year, month, 1),
    scheduled_date_to: isoDate(year, month, lastDay.getDate()),
    ...(hospitalFilter && { hospital_id: hospitalFilter }),
  }
  const { data: rawOrders = [], isLoading } = useWorkOrders(woParams)
  const orders = Array.isArray(rawOrders) ? rawOrders : (rawOrders.results ?? [])

  // Group orders by scheduled_date
  const ordersByDate = useMemo(() => {
    const map = {}
    orders.forEach((wo) => {
      const key = wo.scheduled_date
      if (!map[key]) map[key] = []
      map[key].push(wo)
    })
    return map
  }, [orders])

  // Build calendar grid
  const startOffset = firstDay.getDay()
  const daysInMonth = lastDay.getDate()
  const cells = []
  for (let i = 0; i < startOffset; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)
  while (cells.length % 7 !== 0) cells.push(null)

  function prevMonth() {
    if (month === 0) { setYear((y) => y - 1); setMonth(11) }
    else setMonth((m) => m - 1)
    setSelectedDay(null)
  }

  function nextMonth() {
    if (month === 11) { setYear((y) => y + 1); setMonth(0) }
    else setMonth((m) => m + 1)
    setSelectedDay(null)
  }

  const selectedDateKey = selectedDay ? isoDate(year, month, selectedDay) : null
  const selectedOrders = selectedDateKey ? (ordersByDate[selectedDateKey] ?? []) : []
  const isToday = (d) =>
    d && d === today.getDate() && month === today.getMonth() && year === today.getFullYear()

  return (
    <div className="space-y-4 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Calendario de mantenimientos</h1>
          <p className="text-sm text-gray-500 mt-0.5">OTs preventivas programadas</p>
        </div>
        <select
          value={hospitalFilter}
          onChange={(e) => { setHospitalFilter(e.target.value); setSelectedDay(null) }}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none"
        >
          <option value="">Todos los hospitales</option>
          {hospitals.map((h) => (
            <option key={h.id} value={h.id}>{h.name}</option>
          ))}
        </select>
      </div>

      <div className="flex gap-4">
        {/* Calendario */}
        <div className="flex-1 bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
          {/* Navegación mes */}
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <button onClick={prevMonth}
              className="text-gray-500 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-50">
              ‹
            </button>
            <h2 className="text-base font-semibold text-gray-800">
              {MONTHS_ES[month]} {year}
            </h2>
            <button onClick={nextMonth}
              className="text-gray-500 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-50">
              ›
            </button>
          </div>

          {/* Grid */}
          <div className="grid grid-cols-7">
            {DAYS_OF_WEEK.map((d) => (
              <div key={d} className="text-center text-xs text-gray-500 font-medium py-2 border-b">
                {d}
              </div>
            ))}
            {cells.map((day, i) => {
              if (!day) return <div key={`e-${i}`} className="min-h-[72px] bg-gray-50/50" />
              const dateKey = isoDate(year, month, day)
              const dayOrders = ordersByDate[dateKey] ?? []
              const isSelected = day === selectedDay
              return (
                <div
                  key={day}
                  onClick={() => setSelectedDay(day === selectedDay ? null : day)}
                  className={`min-h-[72px] p-1.5 border-b border-r border-gray-50 cursor-pointer transition-colors
                    ${isSelected ? 'bg-brand/10' : 'hover:bg-gray-50'}`}
                >
                  <span className={`text-xs font-medium inline-block w-6 h-6 flex items-center justify-center rounded-full
                    ${isToday(day) ? 'bg-brand text-white' : 'text-gray-600'}`}>
                    {day}
                  </span>
                  {dayOrders.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-0.5">
                      {dayOrders.slice(0, 4).map((wo) => (
                        <span key={wo.id} className={`w-2 h-2 rounded-full ${statusDot(wo.status)}`}
                          title={formatWoCode(wo)} />
                      ))}
                      {dayOrders.length > 4 && (
                        <span className="text-xs text-gray-500 leading-none">+{dayOrders.length - 4}</span>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {isLoading && (
            <div className="flex justify-center py-3 border-t">
              <svg className="animate-spin h-4 w-4 text-brand" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            </div>
          )}
        </div>

        {/* Panel derecho — detalle del día */}
        <div className="w-72 flex-shrink-0 bg-white rounded-xl border border-gray-200 shadow-card">
          {!selectedDay ? (
            <div className="flex flex-col items-center justify-center h-full py-12 text-gray-500">
              <Icon name="calendar" className="w-9 h-9 mx-auto mb-2 text-gray-400" />
              <p className="text-sm text-center px-4">Haz clic en un día para ver las OTs</p>
            </div>
          ) : (
            <div className="p-4 space-y-3">
              <h3 className="font-semibold text-gray-800 text-sm">
                {selectedDay} de {MONTHS_ES[month]}
              </h3>
              {selectedOrders.length === 0 ? (
                <p className="text-sm text-gray-500">Sin OTs preventivas este día</p>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {selectedOrders.map((wo) => (
                    <div key={wo.id}
                      className="border border-gray-100 rounded-lg p-3 cursor-pointer hover:bg-gray-50"
                      onClick={() => navigate(`/ordenes/${wo.id}`)}>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono text-gray-500">{formatWoCode(wo)}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded-full ${statusBadge(wo.status)}`}>
                          {woStatusLabel(wo.status)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-800 mt-1 line-clamp-2">{wo.title}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{wo.asset?.name ?? '—'}</p>
                      {wo.assigned_to?.full_name && (
                        <p className="text-xs text-gray-500 flex items-center gap-1">
                          <Icon name="profile" className="w-3.5 h-3.5 flex-shrink-0" />
                          {wo.assigned_to.full_name}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Leyenda */}
      <div className="flex gap-4 text-xs text-gray-500">
        <span><span className="inline-block w-2 h-2 rounded-full bg-gray-300 mr-1" />Pendiente</span>
        <span><span className="inline-block w-2 h-2 rounded-full bg-blue-400 mr-1" />En proceso</span>
        <span><span className="inline-block w-2 h-2 rounded-full bg-yellow-400 mr-1" />En revisión</span>
        <span><span className="inline-block w-2 h-2 rounded-full bg-green-500 mr-1" />Completada</span>
        <span><span className="inline-block w-2 h-2 rounded-full bg-red-400 mr-1" />Cancelada</span>
      </div>
    </div>
  )
}

function statusDot(status) {
  const m = {
    PENDING: 'bg-gray-300',
    IN_PROGRESS: 'bg-blue-400',
    IN_REVIEW: 'bg-yellow-400',
    COMPLETED: 'bg-green-500',
    CANCELLED: 'bg-red-400',
  }
  return m[status] ?? 'bg-gray-300'
}

function statusBadge(status) {
  const m = {
    PENDING: 'bg-gray-100 text-gray-600',
    IN_PROGRESS: 'bg-blue-50 text-blue-700',
    IN_REVIEW: 'bg-yellow-50 text-yellow-700',
    COMPLETED: 'bg-green-50 text-green-700',
    CANCELLED: 'bg-red-50 text-red-600',
  }
  return m[status] ?? 'bg-gray-100 text-gray-500'
}
