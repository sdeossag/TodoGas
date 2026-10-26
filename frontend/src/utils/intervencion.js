// Fecha de intervención corregida en revisión: reglas iguales a las del servidor.

// Misma tolerancia que el servidor (device_time.TOLERANCIA): 5 minutos.
const TOLERANCIA_MS = 5 * 60 * 1000

const pad = (n) => String(n).padStart(2, '0')

/** ISO del servidor -> valor de un <input type="datetime-local"> en hora local. */
export function aInputLocal(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export const cuando = (iso) =>
  new Date(iso).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })

/**
 * Valida inicio y fin (valores de datetime-local) con las mismas reglas del
 * servidor. Devuelve { start, end } con el mensaje de cada campo, o {}.
 */
export function validarIntervencion(start, end, creada, ahora = Date.now()) {
  const errores = {}
  const t = (v) => (v ? new Date(v).getTime() : NaN)
  const ini = t(start)
  const fin = t(end)
  if (!start) errores.start = 'Indica cuándo empezó.'
  else if (Number.isNaN(ini)) errores.start = 'Fecha y hora no válidas.'
  if (!end) errores.end = 'Indica cuándo terminó.'
  else if (Number.isNaN(fin)) errores.end = 'Fecha y hora no válidas.'

  const creadaMs = creada ? new Date(creada).getTime() : NaN
  if (!errores.start) {
    if (ini > ahora + TOLERANCIA_MS) errores.start = 'No puede estar en el futuro.'
    else if (!Number.isNaN(creadaMs) && ini < creadaMs - TOLERANCIA_MS)
      errores.start = `No puede ser antes de que se creara la orden (${cuando(creada)}).`
  }
  if (!errores.end) {
    if (fin > ahora + TOLERANCIA_MS) errores.end = 'No puede estar en el futuro.'
    else if (!errores.start && fin < ini) errores.end = 'El fin no puede ser antes del inicio.'
  }
  return errores
}
