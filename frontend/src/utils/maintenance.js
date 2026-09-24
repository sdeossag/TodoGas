/**
 * Etiquetas y formatos del modelo de tareas (planes de tareas, tareas
 * pendientes). Los nombres de las fechas son los de Fracttal, que es como las
 * conoce el cliente: calculada, programada y de realización.
 */

// Condiciones de los activadores "cuando" (Fracttal: Lectura Cuando).
export const COMPARATOR_LABELS = {
  EQ: 'Igual a', NE: 'Diferente a', GT: 'Mayor que', GTE: 'Mayor o igual a', LT: 'Menor que', LTE: 'Menor o igual a',
}

export const FREQ_UNITS = [
  { value: 'DAYS', one: 'día', many: 'días' },
  { value: 'WEEKS', one: 'semana', many: 'semanas' },
  { value: 'MONTHS', one: 'mes', many: 'meses' },
  { value: 'YEARS', one: 'año', many: 'años' },
]

export const TRIGGERS = [
  { value: 'DATE', label: 'Por fecha' },
  { value: 'EVENT', label: 'Por evento' },
]

export const TASK_STATUS = {
  PENDING: { label: 'Pendiente', cls: 'bg-gray-100 text-gray-700' },
  SCHEDULED: { label: 'Programada', cls: 'bg-blue-50 text-blue-700' },
  DONE: { label: 'Finalizada', cls: 'bg-green-50 text-green-700' },
  CANCELLED: { label: 'Cancelada', cls: 'bg-red-50 text-red-600' },
}

export const PRIORITIES = [
  { value: 'HIGH', label: 'Alta' },
  { value: 'MEDIUM', label: 'Media' },
  { value: 'LOW', label: 'Baja' },
]

export const PRIORITY_BADGE = {
  HIGH: 'bg-red-100 text-red-700',
  MEDIUM: 'bg-yellow-100 text-yellow-700',
  LOW: 'bg-gray-100 text-gray-500',
}

export function priorityLabel(value) {
  return PRIORITIES.find((p) => p.value === value)?.label ?? value ?? '—'
}

/** "Cada 6 meses", "Cada mes", "Por evento"; con "· 1 vez" si no se repite siempre. */
export function formatFrequency(task) {
  if (!task) return '—'
  let base
  const numero = (n) => Number(n).toLocaleString('es-CO', { maximumFractionDigits: 3 })
  if (task.trigger === 'EVENT') {
    base = 'Por evento'
  } else if (task.trigger === 'EVERY') {
    base = `Cada ${numero(task.meter_interval)} ${task.meter_unit_symbol ?? ''}`.trim()
  } else if (task.trigger === 'WHEN') {
    const cond = COMPARATOR_LABELS[task.meter_comparator]?.toLowerCase() ?? ''
    base = `Cuando ${task.meter_unit_label ?? 'la lectura'} sea ${cond} ${numero(task.meter_threshold)}`
  } else {
    const unit = FREQ_UNITS.find((u) => u.value === task.frequency_unit)
    const n = task.frequency_value
    if (!unit || !n) return '—'
    base = n === 1 ? `Cada ${unit.one}` : `Cada ${n} ${unit.many}`
  }
  if (task.repeat_count) {
    base += ` · ${task.repeat_count === 1 ? '1 vez' : `${task.repeat_count} veces`}`
  }
  return base
}

/** Minutos de una duración de DRF ("01:10:00" o "1 02:00:00"). */
export function durationMinutes(value) {
  if (!value) return 0
  const match = String(value).match(/^(?:(\d+) )?(\d+):(\d+):(\d+)/)
  if (!match) return 0
  const [, dias, h, m] = match
  return (parseInt(dias || '0', 10) * 24 + parseInt(h, 10)) * 60 + parseInt(m, 10)
}

export function formatMinutes(total) {
  if (!total) return '—'
  const h = Math.floor(total / 60)
  const m = total % 60
  if (h === 0) return `${m} min`
  return m ? `${h} h ${m} min` : `${h} h`
}

export function formatDuration(value) {
  return formatMinutes(durationMinutes(value))
}

/** Horas y minutos del formulario a la duración que espera la API. */
export function buildDuration(hours, minutes) {
  const h = parseInt(hours, 10) || 0
  const m = parseInt(minutes, 10) || 0
  if (h === 0 && m === 0) return null
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00`
}

export function splitDuration(value) {
  const total = durationMinutes(value)
  if (!total) return { hours: '', minutes: '' }
  return { hours: String(Math.floor(total / 60)), minutes: String(total % 60) }
}

function toIso(d) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** Fecha de hoy como AAAA-MM-DD en la zona del navegador. */
export function todayIso() {
  return toIso(new Date())
}

/**
 * Suma una frecuencia a una fecha AAAA-MM-DD igual que el backend
 * (relativedelta): 30 de agosto + 6 meses = 28 de febrero, no 2 de marzo.
 */
export function addFrequency(iso, value, unit) {
  const n = parseInt(value, 10)
  if (!iso || !n || n <= 0) return null
  const [y, m, d] = iso.split('-').map(Number)
  if (unit === 'DAYS' || unit === 'WEEKS') {
    return toIso(new Date(y, m - 1, d + n * (unit === 'WEEKS' ? 7 : 1)))
  }
  const meses = unit === 'YEARS' ? n * 12 : n
  const destino = new Date(y, m - 1 + meses, 1)
  const ultimoDia = new Date(destino.getFullYear(), destino.getMonth() + 1, 0).getDate()
  destino.setDate(Math.min(d, ultimoDia))
  return toIso(destino)
}

export function formatDate(iso, opts = { day: '2-digit', month: 'short', year: 'numeric' }) {
  if (!iso) return '—'
  const d = new Date(String(iso).length === 10 ? `${iso}T00:00:00` : iso)
  return d.toLocaleDateString('es-CO', opts)
}

/** Días desde hoy hasta la fecha (negativo si ya pasó). */
export function daysFromToday(iso) {
  if (!iso) return null
  const hoy = new Date(`${todayIso()}T00:00:00`)
  const fecha = new Date(`${iso}T00:00:00`)
  return Math.round((fecha - hoy) / 86400000)
}

export function relativeDue(iso) {
  const dias = daysFromToday(iso)
  if (dias === null) return ''
  if (dias === 0) return 'hoy'
  if (dias === 1) return 'mañana'
  if (dias === -1) return 'ayer'
  return dias < 0 ? `hace ${-dias} días` : `en ${dias} días`
}
