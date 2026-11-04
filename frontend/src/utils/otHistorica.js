// OTs historicas importadas de Fracttal: son solo consulta. Aqui va lo que la
// pantalla decide a partir de los datos de la OT, sin tocar React.

export function esHistorica(wo) {
  return Boolean(wo && wo.origin)
}

/** Texto del aviso de arriba del detalle, o null si la OT es nuestra. */
export function avisoHistorica(wo) {
  if (!esHistorica(wo)) return null
  const folio = wo.fracttal_folio ? ` · folio N° ${wo.fracttal_folio}` : ''
  return `OT histórica importada de Fracttal${folio}. Solo consulta.`
}

/** Etiqueta y valor de «Asignado a»: en una histórica, quien ejecutó en Fracttal. */
export function asignadoA(wo) {
  if (esHistorica(wo)) {
    return { etiqueta: 'Ejecutó (Fracttal)', valor: wo.external_executor || '—' }
  }
  return { etiqueta: 'Asignado a', valor: wo?.assigned_to?.full_name ?? '—' }
}

/** Aviso de la pestaña Evidencia, o null si no queda nada por traer. */
export function textoFotosPendientes(wo) {
  if (!esHistorica(wo)) return null
  const n = Number(wo.fracttal_photos_pending) || 0
  if (n <= 0) return null
  return n === 1
    ? '1 foto quedó en Fracttal y aún no se ha traído'
    : `${n} fotos quedaron en Fracttal y aún no se han traído`
}

/** Etiqueta pequeña de la lista junto al código. */
export function etiquetaOrigen(wo) {
  return esHistorica(wo) ? 'Fracttal' : null
}
