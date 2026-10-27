/**
 * Fecha de inicio al asignar un protocolo y checklist predeterminado por activo
 * (revisión del 2026-10-23). Lógica pura, sin React, para poder probarla.
 */

/** Cuerpo de assign-assets / assign-locations; la fecha vacía no viaja (= como antes). */
export function cuerpoAsignacion(clave, ids, fechaInicio) {
  const cuerpo = { [clave]: ids }
  const fecha = (fechaInicio ?? '').trim()
  if (fecha) cuerpo.start_date = fecha
  return cuerpo
}

/** 'YYYY-MM-DD' de hoy en hora local (no UTC: de noche cambiaría de día). */
export function hoyISO(ahora = new Date()) {
  const p = (n) => String(n).padStart(2, '0')
  return `${ahora.getFullYear()}-${p(ahora.getMonth() + 1)}-${p(ahora.getDate())}`
}

/** Aviso bajo el campo de fecha: pasada sale vencida, futura espera, vacía = como siempre. */
export function avisoFechaInicio(fechaInicio, hoy = hoyISO()) {
  const fecha = (fechaInicio ?? '').trim()
  if (!fecha) return null
  if (fecha < hoy) return 'La fecha ya pasó: la primera tarea saldrá vencida.'
  if (fecha === hoy) return 'La primera tarea vence hoy.'
  return null
}

/**
 * Versión de checklist con la que se preselecciona un activo en la OT manual:
 * la vigente de su plantilla predeterminada, o '' si no tiene o no está publicada.
 */
export function versionPredeterminada(activo, plantillas) {
  const id = activo?.default_checklist_template
  if (!id) return ''
  const plantilla = (plantillas ?? []).find((t) => t.id === id && t.current_version_id)
  return plantilla ? plantilla.current_version_id : ''
}
