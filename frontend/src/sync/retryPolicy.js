/**
 * Politica de reintentos del motor de sincronizacion.
 *
 * Es logica pura, sin red ni base de datos, para poder probarla en Node
 * (retryPolicy.test.mjs). Un fallo es de uno de dos tipos:
 *
 *   - transitorio: la peticion no llego, o el servidor no pudo atenderla ahora
 *     (sin respuesta, 5xx, 408, 429, y 401 mientras se renueva la sesion).
 *     Se reintenta solo, con espera creciente.
 *   - permanente: el servidor la leyo y la rechazo (el resto de 4xx). Repetirla
 *     da lo mismo, asi que el elemento pasa a "requiere atencion" y deja de
 *     reintentarse solo hasta que el tecnico lo pida.
 */

export const TRANSIENT = 'transient'
export const PERMANENT = 'permanent'

export const BACKOFF_BASE_MS = 60 * 1000 // 1 min, luego 2, 4, 8...
export const BACKOFF_MAX_MS = 30 * 60 * 1000 // tope de 30 min

// Estados guardados por elemento en sync_state.
export const STATUS_RETRY = 'retry'
export const STATUS_ATTENTION = 'attention'

const TRANSIENT_STATUS = new Set([408, 429])

/**
 * Clasifica el error de una peticion.
 * 401 cuenta como transitorio: es la sesion vencida y se arregla volviendo a
 * entrar, no tocando la evidencia, que no debe quedar marcada como rechazada.
 */
export function classifyError(error) {
  const status = error?.response?.status ?? null
  if (status == null) {
    // Sin respuesta: la peticion no llego al servidor (red, tiempo agotado).
    // Un Error local (por ejemplo una fila corrupta) no es de red y no se
    // arregla esperando.
    const deRed = !!(error?.isAxiosError || error?.request || error?.code)
    return { kind: deRed ? TRANSIENT : PERMANENT, status: null }
  }
  if (status >= 500 || status === 401 || TRANSIENT_STATUS.has(status)) {
    return { kind: TRANSIENT, status }
  }
  if (status >= 400) return { kind: PERMANENT, status }
  // Una respuesta 3xx/inesperada no se puede dar por buena ni por rechazada.
  return { kind: TRANSIENT, status }
}

/**
 * Espera antes del proximo intento, tras `attempts` fallos seguidos.
 * Exponencial con jitter (+-25%) para que muchos telefonos que volvieron a
 * tener red a la vez no golpeen al servidor juntos. `random` se inyecta en las
 * pruebas.
 */
export function backoffDelayMs(attempts, random = Math.random) {
  const n = Math.max(1, Math.floor(attempts || 1))
  const base = Math.min(BACKOFF_MAX_MS, BACKOFF_BASE_MS * 2 ** (n - 1))
  return Math.min(BACKOFF_MAX_MS, Math.round(base * (0.75 + random() * 0.5)))
}

/** Estado nuevo de un elemento tras un fallo. */
export function nextState(previous, error, now = Date.now(), random = Math.random) {
  const { kind, status } = classifyError(error)
  const attempts = (previous?.attempts ?? 0) + 1
  if (kind === PERMANENT) {
    return { status: STATUS_ATTENTION, attempts, next_retry_at: null, http_status: status }
  }
  return {
    status: STATUS_RETRY,
    attempts,
    next_retry_at: now + backoffDelayMs(attempts, random),
    http_status: status,
  }
}

/** ¿Toca intentar este elemento ahora? `state` es su fila de sync_state, si tiene. */
export function dueNow(state, now = Date.now()) {
  if (!state) return true
  if (state.status === STATUS_ATTENTION) return false
  return state.next_retry_at == null || state.next_retry_at <= now
}

/**
 * Mensaje del servidor en lenguaje legible: `detail` si lo hay; si no, los
 * campos de DRF. Una pagina HTML de error (502 de un proxy) no se muestra tal
 * cual. Sin respuesta, un texto de red.
 */
export function serverMessage(error) {
  const status = error?.response?.status
  const data = error?.response?.data
  if (data && typeof data === 'object') {
    if (data.detail) return String(data.detail).slice(0, 300)
    const partes = Object.values(data).map((v) => (Array.isArray(v) ? v.join(' ') : String(v)))
    const texto = partes.join(' · ').slice(0, 300)
    if (texto) return texto
  }
  if (typeof data === 'string' && data && !/^\s*</.test(data)) return data.slice(0, 300)
  if (status) return `El servidor respondió con el error ${status}.`
  return error?.message || 'No se pudo conectar con el servidor.'
}

/**
 * Backend nuevo: el 400 trae `code: "checklist_completed"`. Los servidores
 * viejos solo traen el texto en español; la regex queda de respaldo y se puede
 * quitar cuando ya no haya ninguno.
 */
export function isChecklistCompleted(error) {
  if (error?.response?.status !== 400) return false
  const data = error.response.data
  if (data?.code === 'checklist_completed') return true
  // La OT ya no esta en curso (la enviaron a revision): el cambio en cola ya
  // no tiene donde aplicarse.
  if (data?.code === 'ot_no_editable') return true
  // Respaldo para servidores sin `code`.
  const texto = typeof data === 'string' ? data : (data?.detail ?? '')
  return /ya est. completado/i.test(texto)
}

/** Que es cada elemento, en palabras del tecnico. */
export const ITEM_LABELS = {
  field_response: 'Una respuesta del checklist',
  checklist_completion: 'El cierre de un checklist',
  block_count: 'La cantidad de tomas de un checklist',
  checklist_pending: 'Los pendientes de un checklist',
  finding: 'Un hallazgo',
  photo: 'Una foto',
  signature: 'Una firma',
  work_order: 'El cambio de estado de la orden',
}

export const itemLabel = (entityType) => ITEM_LABELS[entityType] ?? 'Un dato'
