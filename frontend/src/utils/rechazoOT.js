/**
 * Por qué le devolvieron una OT al técnico.
 *
 * Rechazar en revisión pasa la OT de IN_REVIEW a IN_PROGRESS con un comentario
 * obligatorio. El rechazo sigue vigente mientras la OT esté en curso y ese haya
 * sido el último cambio de estado; si volvió a revisión (o se cerró) ya no aplica.
 *
 * Lee `status_history` (detalle) y, si no viene, `last_rejection` (lista: la app
 * guarda la lista sin historial, y el servidor ya calcula ahí lo mismo).
 */
export function ultimoRechazo(ot) {
  if (!ot || ot.status !== 'IN_PROGRESS') return null

  const historial = Array.isArray(ot.status_history) ? ot.status_history : null
  if (historial) {
    if (historial.length === 0) return null
    const ordenado = historial
      .map((h, i) => ({ h, i }))
      .sort((a, b) => {
        const dt = new Date(a.h.changed_at).getTime() - new Date(b.h.changed_at).getTime()
        return Number.isNaN(dt) || dt === 0 ? a.i - b.i : dt
      })
    const ultimo = ordenado[ordenado.length - 1].h
    if (ultimo.from_status !== 'IN_REVIEW' || ultimo.to_status !== 'IN_PROGRESS') return null
    return {
      motivo: ultimo.comment ?? '',
      por: ultimo.changed_by?.full_name ?? '',
      fecha: ultimo.changed_at ?? null,
    }
  }

  const r = ot.last_rejection
  if (r && typeof r === 'object') {
    return { motivo: r.motivo ?? '', por: r.por ?? '', fecha: r.fecha ?? null }
  }
  return null
}

/** Fecha y hora de Colombia para el aviso. */
export function fechaDeRechazo(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('es-CO', { timeZone: 'America/Bogota', dateStyle: 'medium', timeStyle: 'short' })
}
