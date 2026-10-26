/**
 * Cálculos de presentación del tablero: nada de red ni de React, para poder
 * probarlos con `node --test`.
 */

const MONTH_ABBR = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

/** "2026-10" -> { short: 'Oct', long: 'Oct 2026' } */
export function monthLabel(ym) {
  const [year, month] = String(ym ?? '').split('-')
  const abbr = MONTH_ABBR[parseInt(month, 10) - 1] ?? ym
  return { short: abbr, long: year ? `${abbr} ${year}` : abbr }
}

function pad(n) {
  return String(n).padStart(2, '0')
}

/** Primer y último día de un mes "YYYY-MM", como YYYY-MM-DD (sin zonas horarias). */
export function monthRange(ym) {
  const [y, m] = ym.split('-').map(Number)
  const last = new Date(Date.UTC(y, m, 0)).getUTCDate()
  return { from: `${y}-${pad(m)}-01`, to: `${y}-${pad(m)}-${pad(last)}` }
}

/**
 * Enlace a Tareas pendientes para una barra del gráfico de planificación:
 * `ym` = null para las vencidas. `today` (YYYY-MM-DD) acota el mes en curso a
 * lo que aún no venció, igual que el conteo del servidor.
 */
export function pendingTasksLink({ ym = null, hospitalId = '', today = '' } = {}) {
  const qs = new URLSearchParams()
  if (hospitalId) qs.set('hospital_id', hospitalId)
  if (ym == null) {
    qs.set('overdue', '1')
  } else {
    const { from, to } = monthRange(ym)
    qs.set('due_after', today && today > from && today.slice(0, 7) === ym ? today : from)
    qs.set('due_before', to)
  }
  return `/tareas-pendientes?${qs.toString()}`
}

/** Enlace a un listado de activos filtrado por estado de mantenimiento. */
export function assetsLink(maintenanceStatus, hospitalId = '') {
  const qs = new URLSearchParams({ maintenance_status: maintenanceStatus })
  if (hospitalId) qs.set('hospital_id', hospitalId)
  return `/activos?${qs.toString()}`
}

/** Segmentos de una barra apilada: ancho en % de cada categoría con valor. */
export function shares(items) {
  const total = items.reduce((a, i) => a + (i.value || 0), 0)
  if (!total) return []
  return items.filter((i) => i.value > 0).map((i) => ({ ...i, pct: (i.value / total) * 100 }))
}
