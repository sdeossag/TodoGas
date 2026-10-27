// Dar de baja o reactivar varios activos a la vez. Lógica pura: selección,
// límite (el mismo que impone el servidor) y los textos del resumen.

export const MAX_ACTIVOS_MASIVO = 200

export const ACCION_BAJA = 'DECOMMISSIONED'
export const ACCION_REACTIVAR = 'ACTIVE'

export const INICIO_HOY = 'today'
export const INICIO_ULTIMO_CIERRE = 'last_close'

export const OPCIONES_INICIO = [
  { value: INICIO_HOY, label: 'Desde hoy (recomendado)', ayuda: 'Las tareas de su protocolo quedan programadas para hoy.' },
  { value: INICIO_ULTIMO_CIERRE, label: 'Según su último mantenimiento', ayuda: 'Cada tarea toma la fecha que le toca por su último cierre; puede salir vencida.' },
]

export function excedeLimite(cantidad) {
  return cantidad > MAX_ACTIVOS_MASIVO
}

export function avisoLimite() {
  return `Puedes cambiar hasta ${MAX_ACTIVOS_MASIVO} activos a la vez.`
}

/** Validación de la selección: devuelve el motivo por el que no se puede, o null. */
export function validarSeleccion(cantidad) {
  if (cantidad < 1) return 'Elige al menos un activo.'
  if (excedeLimite(cantidad)) return avisoLimite()
  return null
}

export function textoSeleccion(cantidad) {
  return `${cantidad} ${cantidad === 1 ? 'activo seleccionado' : 'activos seleccionados'}`
}

export function todasMarcadas(seleccion, visibles) {
  const ids = visibles.map((a) => a.id)
  return ids.length > 0 && ids.every((id) => seleccion.has(id))
}

/** Marca todas las filas visibles, o las desmarca si ya estaban todas marcadas. */
export function alternarTodas(seleccion, visibles) {
  const todas = todasMarcadas(seleccion, visibles)
  const nueva = new Set(seleccion)
  for (const a of visibles) {
    if (todas) nueva.delete(a.id)
    else nueva.add(a.id)
  }
  return nueva
}

export function tituloAccion(accion) {
  return accion === ACCION_BAJA ? 'Dar de baja' : 'Reactivar'
}

function plural(n, uno, varios) {
  return `${n} ${n === 1 ? uno : varios}`
}

/** Cuántos activos cambian y cuántos ya estaban en ese estado. */
export function textoCambian(resumen, accion) {
  const { changed, unchanged } = resumen
  const verbo = accion === ACCION_BAJA ? 'se darán de baja' : 'se reactivarán'
  const verboUno = accion === ACCION_BAJA ? 'se dará de baja' : 'se reactivará'
  const partes = []
  partes.push(changed === 0
    ? 'Ningún activo cambia de estado.'
    : `${plural(changed, 'activo', 'activos')}: ${changed === 1 ? verboUno : verbo}.`)
  if (unchanged > 0) {
    const ya = accion === ACCION_BAJA ? 'de baja' : 'activo'
    partes.push(`${plural(unchanged, 'ya está', 'ya están')} ${ya} y no ${unchanged === 1 ? 'cambia' : 'cambian'}.`)
  }
  return partes.join(' ')
}

/** Lo que pasa con las tareas, según la acción. */
export function textoTareas(resumen, accion, inicio = INICIO_HOY) {
  if (accion === ACCION_BAJA) {
    const n = resumen.cancelled
    if (n === 0) return 'No hay tareas pendientes que anular.'
    return n === 1
      ? 'Se anulará 1 tarea pendiente. Queda en el historial como cancelada; nada se borra.'
      : `Se anularán ${n} tareas pendientes. Quedan en el historial como canceladas; nada se borra.`
  }
  const n = resumen.reopened
  const cuando = inicio === INICIO_HOY ? 'programadas para hoy' : 'con la fecha que les toca por su último mantenimiento'
  if (n === 0) return 'No hay tareas del protocolo que abrir.'
  return n === 1
    ? `Se abrirá 1 tarea del protocolo, ${cuando}.`
    : `Se abrirán ${n} tareas del protocolo, ${cuando}.`
}

/** Lo mismo que textoTareas, en pasado, para el mensaje final. */
export function textoTareasHechas(resumen, accion, inicio = INICIO_HOY) {
  if (accion === ACCION_BAJA) {
    const n = resumen.cancelled
    return n === 0 ? 'No había tareas pendientes que anular.' : `${plural(n, 'tarea pendiente anulada', 'tareas pendientes anuladas')}.`
  }
  const n = resumen.reopened
  const cuando = inicio === INICIO_HOY ? 'programadas para hoy' : 'con la fecha de su último mantenimiento'
  return n === 0 ? 'No había tareas del protocolo que abrir.' : `${plural(n, 'tarea del protocolo abierta', 'tareas del protocolo abiertas')}, ${cuando}.`
}

/** Aviso de las OT abiertas que conservan tareas, o null si no hay. */
export function textoOts(resumen) {
  const ots = resumen.in_work_orders ?? []
  if (ots.length === 0) return null
  return `${plural(ots.length, 'OT abierta conserva', 'OT abiertas conservan')} tareas de estos activos (${ots.join(', ')}). No se tocan; al cerrarse no se programa la siguiente.`
}

/** Mensaje final tras aplicar el cambio. */
export function textoResultado(resumen, accion) {
  const hecho = accion === ACCION_BAJA ? 'dados de baja' : 'reactivados'
  const hechoUno = accion === ACCION_BAJA ? 'dado de baja' : 'reactivado'
  const { changed, unchanged } = resumen
  let base = changed === 0
    ? 'No hubo cambios.'
    : `${plural(changed, 'activo', 'activos')} ${changed === 1 ? hechoUno : hecho}.`
  if (unchanged > 0) base += ` ${plural(unchanged, 'ya estaba', 'ya estaban')} en ese estado.`
  return base
}
