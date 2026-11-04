/**
 * Lógica pura de la pestaña "JSON del extractor" de Importar desde Fracttal.
 * Sin React, para probarla con node --test.
 */

export const LIMITE_JSON_MB = 100

export function errorDeArchivoJson(file) {
  if (!file) return ''
  if (!file.name?.toLowerCase().endsWith('.json')) return 'El archivo debe ser un JSON (.json) del extractor de Fracttal.'
  if (file.size > LIMITE_JSON_MB * 1024 * 1024) return `El archivo supera los ${LIMITE_JSON_MB} MB.`
  return ''
}

function plural(n, uno, varios) {
  return `${n} ${n === 1 ? uno : varios}`
}

export function puedeImportarJson(resumen) {
  if (!resumen) return false
  if ((resumen.errors_count ?? 0) > 0) return false
  const total = (resumen.hospitals?.create?.length ?? 0) +
    (resumen.locations?.create ?? 0) + (resumen.locations?.update ?? 0) +
    (resumen.assets?.create ?? 0) + (resumen.assets?.update ?? 0) +
    (resumen.work_orders?.create ?? 0)
  return total > 0
}

// Lo que se va a guardar (o se guardó), en frases cortas.
export function textoResultadoJson(r) {
  if (!r) return []
  const partes = []
  const h = r.hospitals?.create?.length ?? 0
  if (h) partes.push(plural(h, 'hospital nuevo', 'hospitales nuevos'))
  const l = r.locations
  if (l?.create || l?.update) partes.push(`ubicaciones: ${l.create} nuevas, ${l.update} se actualizan`)
  const a = r.assets
  if (a?.create || a?.update) partes.push(`equipos: ${a.create} nuevos, ${a.update} se actualizan`)
  const p = r.plans
  if (p?.create || p?.update) partes.push(`protocolos: ${p.create} nuevos, ${p.update} existentes`)
  const o = r.work_orders
  if (o?.create) partes.push(plural(o.create, 'OT histórica', 'OT históricas'))
  return partes
}
