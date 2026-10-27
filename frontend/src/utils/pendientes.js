/**
 * Pendientes del checklist ("no se pudo revisar"), la misma regla que el
 * servidor (ChecklistResponseViewSet.set_pending).
 *
 * Un pendiente es un campo (field + toma) o un bloque repetible completo
 * (group + toma, sin field), con un motivo obligatorio. Responder el campo, o
 * algo del bloque, lo quita. Un pendiente cuenta como no completo.
 */

const rep = (n) => Number(n ?? 0) || 0

/** Es el pendiente de ese campo en esa toma. */
export function esDeCampo(p, fieldId, repetition = 0) {
  return !!p.field && String(p.field) === String(fieldId) && rep(p.repetition) === rep(repetition)
}

/** Es el pendiente de ese bloque (grupo y toma). */
export function esDeBloque(p, group, repetition) {
  return !p.field && p.group === group && rep(p.repetition) === rep(repetition)
}

export function pendienteDeCampo(lista, fieldId, repetition = 0) {
  return (lista ?? []).find((p) => esDeCampo(p, fieldId, repetition)) ?? null
}

export function pendienteDeBloque(lista, group, repetition) {
  return (lista ?? []).find((p) => esDeBloque(p, group, repetition)) ?? null
}

/** Agrega o reemplaza (mismo campo/bloque y toma). El motivo se recorta. */
export function conPendiente(lista, { field = null, group = '', repetition = 0, reason, marked_at }) {
  const motivo = String(reason ?? '').trim()
  if (!motivo) throw new Error('Di por qué quedó pendiente.')
  const nuevo = {
    field: field || null,
    group: field ? '' : group,
    repetition: rep(repetition),
    reason: motivo.slice(0, 200),
    marked_at: marked_at ?? new Date().toISOString(),
  }
  const mismo = (p) => (nuevo.field ? esDeCampo(p, nuevo.field, nuevo.repetition)
    : esDeBloque(p, nuevo.group, nuevo.repetition))
  const previa = (lista ?? []).find(mismo)
  return [
    ...(lista ?? []).filter((p) => !mismo(p)),
    previa ? { ...previa, reason: nuevo.reason } : nuevo,
  ]
}

/** Quita el pendiente de un campo o bloque ("Ya pude revisarlo"). */
export function sinPendiente(lista, { field = null, group = '', repetition = 0 }) {
  return (lista ?? []).filter((p) =>
    !(field ? esDeCampo(p, field, repetition) : esDeBloque(p, group, repetition))
  )
}

/**
 * Al responder un campo: se va su pendiente y el del bloque al que pertenece
 * en esa toma (el tecnico ya volvio al cubiculo).
 */
export function sinPendientesAlResponder(lista, response, field, repetition = 0) {
  const repetible = !!field.group && (response?.repeatable_groups ?? []).includes(field.group)
  return (lista ?? []).filter((p) =>
    !(esDeCampo(p, field.id, repetition) || (repetible && esDeBloque(p, field.group, repetition)))
  )
}

/** Al bajar la cantidad de tomas, los pendientes de las que ya no existen se van. */
export function sinPendientesDeTomasQueSobran(lista, group, cuantas) {
  return (lista ?? []).filter((p) => !(p.group === group && rep(p.repetition) > cuantas))
}

/** "Cubículo 7: pendiente — aislado por aerosoles", como lo dice el servidor. */
export function textoPendiente(p, fields = []) {
  let nombre
  if (p.field) {
    const campo = fields.find((f) => String(f.id) === String(p.field))
    nombre = campo?.label ?? 'Campo'
    if (campo?.group && rep(p.repetition)) nombre = `${campo.group} ${p.repetition}: ${nombre}`
  } else {
    nombre = `${p.group ?? ''} ${p.repetition ?? ''}`.trim()
  }
  return `${nombre}: pendiente — ${p.reason ?? ''}`
}

/** Los pendientes vigentes del checklist: los que aun no tienen respuesta. */
export function pendientesVigentes(response) {
  const respondidas = new Set(
    (response?.field_responses ?? []).map((fr) => `${fr.field}:${rep(fr.repetition)}`)
  )
  return (response?.pendientes ?? []).filter(
    (p) => !p.field || !respondidas.has(`${p.field}:${rep(p.repetition)}`)
  )
}

/** Resumen para la lista de tareas de la OT, como lo da el servidor. */
export function resumenPendientes(response) {
  const vigentes = pendientesVigentes(response)
  return {
    pending_count: vigentes.length,
    pending: vigentes.map((p) => textoPendiente(p, response?.version_fields ?? [])),
  }
}

/**
 * Los pendientes de todas las tareas de la OT, como los nombra el servidor al
 * negar el envio a revision. Con varias tareas se antepone el activo.
 */
export function pendientesDeLaOt(tasks) {
  const vigentes = (tasks ?? []).filter((t) => t.status !== 'CANCELLED')
  const textos = []
  for (const t of vigentes) {
    for (const texto of t.checklist?.pending ?? []) {
      textos.push(vigentes.length > 1 && t.asset?.name ? `${t.asset.name} · ${texto}` : texto)
    }
  }
  return textos
}
