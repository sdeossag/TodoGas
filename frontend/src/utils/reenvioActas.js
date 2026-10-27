// Reenviar varias actas por correo desde Reportes. Lógica pura: agrupar lo
// seleccionado por hospital, textos y el límite que también impone el servidor.

export const MAX_ACTAS_REENVIO = 50

/** Solo las actas con OT se pueden reenviar (las consolidadas no tienen). */
export function esReenviable(report) {
  return Boolean(report?.work_order?.id)
}

export function excedeLimite(cantidad) {
  return cantidad > MAX_ACTAS_REENVIO
}

export function textoSeleccion(cantidad) {
  return `${cantidad} ${cantidad === 1 ? 'acta seleccionada' : 'actas seleccionadas'}`
}

export function avisoLimite() {
  return `Puedes reenviar hasta ${MAX_ACTAS_REENVIO} actas a la vez.`
}

/** Marca todas las visibles, o las desmarca si ya estaban todas marcadas. */
export function alternarTodas(seleccion, visibles) {
  const ids = visibles.filter(esReenviable).map((r) => r.id)
  const todas = ids.length > 0 && ids.every((id) => seleccion.has(id))
  const nueva = new Set(seleccion)
  for (const id of ids) {
    if (todas) nueva.delete(id)
    else nueva.add(id)
  }
  return nueva
}

export function todasMarcadas(seleccion, visibles) {
  const ids = visibles.filter(esReenviable).map((r) => r.id)
  return ids.length > 0 && ids.every((id) => seleccion.has(id))
}

/**
 * Las actas seleccionadas agrupadas por hospital, en orden alfabético:
 * [{ hospital_id, name, contact_email, count }]. `contact_email` queda vacío
 * si el hospital no tiene correo (o la lista no lo trae).
 */
export function agruparPorHospital(reports, seleccion) {
  const grupos = new Map()
  for (const r of reports) {
    if (!seleccion.has(r.id) || !esReenviable(r)) continue
    const h = r.work_order.hospital ?? {}
    const clave = h.id ?? ''
    if (!grupos.has(clave)) {
      grupos.set(clave, {
        hospital_id: h.id ?? '',
        name: h.name || 'Sin hospital',
        contact_email: h.contact_email || '',
        count: 0,
      })
    }
    grupos.get(clave).count += 1
  }
  return [...grupos.values()].sort((a, b) => a.name.localeCompare(b.name, 'es'))
}

export function textoGrupo(grupo) {
  const actas = `${grupo.count} ${grupo.count === 1 ? 'acta' : 'actas'}`
  return grupo.contact_email ? `${actas} → ${grupo.contact_email}` : `${actas} (sin correo de contacto)`
}

/** Cuántas actas irán a un correo y cuántas se saltarán por falta de correo. */
export function resumenGrupos(grupos) {
  let conCorreo = 0
  let sinCorreo = 0
  for (const g of grupos) {
    if (g.contact_email) conCorreo += g.count
    else sinCorreo += g.count
  }
  return { conCorreo, sinCorreo }
}
