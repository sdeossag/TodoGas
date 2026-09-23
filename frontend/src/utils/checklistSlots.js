/**
 * Bloques repetibles del checklist: la misma regla que ChecklistResponse.slots
 * en el servidor.
 *
 * Un campo que no se repite se responde una vez (repeticion 0). Uno de un grupo
 * repetible, una vez por toma (1..N), donde N sale de block_counts: lo que dijo
 * el plan, o lo que ajusto el tecnico en campo.
 */

export function isRepeatable(response, group) {
  return !!group && (response?.repeatable_groups ?? []).includes(group)
}

export function countFor(response, group) {
  if (!isRepeatable(response, group)) return 1
  return Math.max(1, parseInt(response?.block_counts?.[group], 10) || 1)
}

/** Clave de una respuesta: campo y toma. */
export function slotKey(fieldId, repetition = 0) {
  return `${fieldId}:${repetition ?? 0}`
}

/** [{ field, repetition }] que el checklist espera. */
export function slots(response, fields = response?.version_fields ?? []) {
  const pares = []
  for (const field of fields) {
    if (isRepeatable(response, field.group)) {
      for (let n = 1; n <= countFor(response, field.group); n += 1) pares.push({ field, repetition: n })
    } else {
      pares.push({ field, repetition: 0 })
    }
  }
  return pares
}

/** Avance como lo da el servidor en la lista de tareas de la OT. */
export function progress(response) {
  const esperadas = slots(response)
  const respondidas = new Set(
    (response?.field_responses ?? []).map((fr) => slotKey(fr.field, fr.repetition))
  )
  const planeadas = response?.planned_block_counts ?? {}
  return {
    answered: esperadas.filter((s) => respondidas.has(slotKey(s.field.id, s.repetition))).length,
    total: esperadas.length,
    required_missing: esperadas.filter(
      (s) => s.field.is_required && !respondidas.has(slotKey(s.field.id, s.repetition))
    ).length,
    block_changes: Object.entries(planeadas)
      .filter(([g, n]) => countFor(response, g) !== n)
      .map(([g, n]) => ({ group: g, planned: n, count: countFor(response, g) })),
  }
}
