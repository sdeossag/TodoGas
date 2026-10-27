/**
 * Acceso a la base offline. Todo el SQL vive aqui; el resto de la app habla
 * con estas funciones y nunca con la conexion directamente.
 *
 * Cuando SQLite no esta disponible (navegador sin soporte) las lecturas
 * devuelven vacio y las escrituras son no-op, sin lanzar.
 */

import { query, ready, run } from './database'
import { contarPendientes, leerArchivo, listarPendientes, marcarSubida } from './photoQueue'
import { PRIORITY_RANK_SQL } from './schema'
import { progress, slotKey } from '../utils/checklistSlots'
import { pendientesVigentes, textoPendiente } from '../utils/pendientes'

const nowISO = () => new Date().toISOString()

// El contrato del driver (query/run) que usa photoQueue.js, sobre la base abierta.
const driver = () => ({ query, run })

/** Identificador local. crypto.randomUUID no existe en contextos no seguros. */
export function newId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID()
  return `local-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`
}

// ── Ordenes de trabajo ───────────────────────────────────────────────────────

/**
 * Vuelca las OT del servidor a SQLite. `raw_json` guarda el objeto completo
 * para poder reconstruir offline la misma forma que devuelve la API.
 */
export async function saveWorkOrdersOffline(workOrders = []) {
  if (!(await ready()) || workOrders.length === 0) return 0

  let saved = 0
  for (const wo of workOrders) {
    try {
      await run(
        `INSERT OR REPLACE INTO offline_work_orders (
          id, wo_number, title, description, task_type, status, priority,
          scheduled_date, asset_id, asset_name, asset_code, hospital_name,
          hospital_id, assigned_to_id, checklist_version_id,
          checklist_response_id, notes, synced_at, offline_uuid, raw_json,
          location_name, assets_count,
          local_status_changed, local_status_comment, detail_json,
          local_status_at, local_status_from
        ) VALUES (?,?,?,?,?,
          -- Un estado cambiado sin red y aun sin subir gana al del servidor: si
          -- no, la sincronizacion mandaria el estado viejo y el cambio se perderia.
          COALESCE((SELECT status FROM offline_work_orders WHERE id = ? AND local_status_changed = 1), ?),
          ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
          COALESCE((SELECT local_status_changed FROM offline_work_orders WHERE id = ?), 0),
          (SELECT local_status_comment FROM offline_work_orders WHERE id = ?),
          (SELECT detail_json FROM offline_work_orders WHERE id = ?),
          (SELECT local_status_at FROM offline_work_orders WHERE id = ?),
          (SELECT local_status_from FROM offline_work_orders WHERE id = ?)
        )`,
        [
          wo.id,
          wo.wo_number ?? null,
          wo.title ?? null,
          wo.description ?? null,
          wo.task_type ?? null,
          wo.id,
          wo.status ?? null,
          wo.priority ?? null,
          wo.scheduled_date ?? null,
          // Columnas de la v1 del esquema: se llenan con el primer activo de
          // la visita, que es lo que muestra la tarjeta cuando solo hay uno.
          wo.assets?.[0]?.id ?? null,
          wo.assets?.[0]?.name ?? null,
          wo.assets?.[0]?.code ?? null,
          wo.hospital?.name ?? null,
          wo.hospital?.id ?? null,
          wo.assigned_to?.id ?? wo.assigned_to ?? null,
          // El checklist es de cada tarea desde la fase 3: estas dos columnas
          // de la v1 quedan vacias y nadie las lee (ver getOfflineWorkOrderDetail).
          null,
          null,
          wo.notes ?? null,
          nowISO(),
          wo.id, // offline_uuid: para las que vienen del servidor basta el id
          JSON.stringify(wo),
          wo.location?.path ?? wo.location?.name ?? null,
          wo.assets_count ?? null,
          // INSERT OR REPLACE borra y reinserta la fila: lo que solo existe en
          // el telefono (estado cambiado sin red, detalle descargado) se copia
          // de la fila anterior o se perderia al refrescar la lista.
          wo.id,
          wo.id,
          wo.id,
          wo.id,
          wo.id,
        ]
      )
      saved += 1
    } catch (error) {
      console.warn('[db] no se pudo guardar la OT', wo.id, error?.message ?? error)
    }
  }
  return saved
}

/** Reconstruye la forma que devuelve la API a partir de raw_json. */
function hydrateWorkOrder(row) {
  let raw = {}
  try {
    raw = JSON.parse(row.raw_json ?? '{}')
  } catch {
    raw = {}
  }
  return {
    ...raw,
    id: row.id,
    wo_number: row.wo_number,
    title: row.title,
    description: row.description,
    task_type: row.task_type,
    // El estado local gana: puede haberse cambiado sin conexion.
    status: row.status,
    priority: row.priority,
    scheduled_date: row.scheduled_date,
    _fromOffline: true,
    _localStatusChanged: row.local_status_changed === 1,
  }
}

export async function getOfflineWorkOrders(assignedToId) {
  if (!(await ready()) || !assignedToId) return []
  const rows = await query(
    `SELECT * FROM offline_work_orders
     WHERE assigned_to_id = ?
       AND status NOT IN ('COMPLETED', 'CANCELLED')
     ORDER BY ${PRIORITY_RANK_SQL}, scheduled_date ASC`,
    [assignedToId]
  )
  return rows.map(hydrateWorkOrder)
}

export async function getOfflineWorkOrder(workOrderId) {
  if (!(await ready()) || !workOrderId) return null
  const rows = await query('SELECT * FROM offline_work_orders WHERE id = ?', [workOrderId])
  return rows.length ? hydrateWorkOrder(rows[0]) : null
}

const parse = (text, fallback) => {
  try {
    return text ? JSON.parse(text) : fallback
  } catch {
    return fallback
  }
}

/**
 * Guarda el detalle de una OT (con sus tareas) para poder abrirla sin red. Si
 * la OT no estaba en la base, entra primero como fila de la lista.
 */
export async function saveWorkOrderDetailOffline(detail) {
  if (!(await ready()) || !detail?.id) return
  const existe = await query('SELECT id FROM offline_work_orders WHERE id = ?', [detail.id])
  if (!existe.length) await saveWorkOrdersOffline([detail])
  await run('UPDATE offline_work_orders SET detail_json = ? WHERE id = ?', [
    JSON.stringify(detail),
    detail.id,
  ])
}

/**
 * Guarda el paquete offline de una OT: su detalle y el checklist de cada
 * tarea, con sus campos y respuestas. Es lo que deja la OT lista para
 * ejecutarse sin red desde el primer campo.
 */
export async function saveWorkOrderBundle(bundle) {
  if (!(await ready()) || !bundle?.work_order) return
  await saveWorkOrderDetailOffline(bundle.work_order)
  for (const checklist of bundle.checklists ?? []) {
    await saveChecklistResponse({ ...checklist, work_order: bundle.work_order.id })
  }
  await saveFindingsFromServer(bundle.work_order.id, bundle.findings ?? [])
}

/**
 * Respuesta del checklist tal como la devolveria la API, armada con lo que se
 * descargo y lo que el tecnico respondio despues en el telefono.
 */
export async function getOfflineChecklistResponse(responseId) {
  if (!(await ready()) || !responseId) return null
  const [row] = await query('SELECT * FROM offline_checklist_responses WHERE id = ?', [responseId])
  if (!row) return null
  const locales = await query('SELECT * FROM offline_field_responses WHERE response_id = ?', [
    responseId,
  ])
  const base = parse(row.response_json, null) ?? {
    id: row.id,
    work_order: row.work_order_id,
    version: row.version_id,
    started_at: row.started_at,
    completed_at: row.completed_at,
    version_fields: parse(row.version_fields_json, []),
    field_responses: [],
  }
  // Una respuesta por campo y toma (bloques repetibles).
  const porCampo = new Map(
    (base.field_responses ?? []).map((fr) => [slotKey(fr.field, fr.repetition), fr])
  )
  for (const local of locales) {
    const clave = slotKey(local.field_id, local.repetition)
    porCampo.set(clave, {
      ...(porCampo.get(clave) ?? {}),
      field: local.field_id,
      repetition: local.repetition ?? 0,
      value: local.value,
      notes: local.notes,
      answered_at: local.answered_at,
      _local: local.synced === 0,
    })
  }
  const reabierta = row.reopened === 1 && !row.local_completed_at
  const armada = {
    ...base,
    // La cantidad de tomas ajustada en el telefono gana sobre la descargada.
    block_counts: parse(row.local_block_counts, null) ?? base.block_counts ?? {},
    field_responses: [...porCampo.values()],
    // Reabierto en el telefono: una lectura del servidor anterior a que la
    // correccion subiera no lo vuelve a cerrar.
    completed_at: reabierta ? null : (base.completed_at ?? row.local_completed_at ?? null),
    // Lo que se dejo pendiente en el telefono gana sobre lo descargado.
    pendientes: row.pendientes_pending === 1
      ? parse(row.local_pendientes, [])
      : (base.pendientes ?? []),
    _fromOffline: true,
    _completionPending: row.completion_pending === 1,
    _reopened: row.reopened === 1,
  }
  // Un pendiente de algo que ya se respondio no cuenta (tambien lo descarta el servidor).
  const vigentes = pendientesVigentes(armada)
  armada.pendientes = vigentes.map((p) => ({
    ...p,
    text: textoPendiente(p, armada.version_fields ?? []),
  }))
  return armada
}

/**
 * Detalle de la OT sin red. El avance de cada tarea se recalcula con lo que el
 * tecnico respondio en el telefono despues de descargarla.
 */
export async function getOfflineWorkOrderDetail(workOrderId) {
  if (!(await ready()) || !workOrderId) return null
  const [row] = await query('SELECT * FROM offline_work_orders WHERE id = ?', [workOrderId])
  if (!row) return null
  const detalle = { ...hydrateWorkOrder(row), ...parse(row.detail_json, {}) }
  // El estado local gana: puede haberse cambiado sin conexion.
  detalle.status = row.status
  detalle._fromOffline = true
  detalle._localStatusChanged = row.local_status_changed === 1

  const tareas = []
  for (const tarea of detalle.tasks ?? []) {
    const responseId = tarea.checklist?.response_id ?? tarea.checklist_response_id
    const respuesta = responseId ? await getOfflineChecklistResponse(responseId) : null
    if (!respuesta) {
      tareas.push(tarea)
      continue
    }
    tareas.push({
      ...tarea,
      checklist: {
        response_id: responseId,
        // Cada toma de un bloque repetible cuenta aparte, como en el servidor.
        ...progress(respuesta),
        // El detalle descargado tambien sabe si el servidor ya lo cerro.
        completed_at:
          respuesta.completed_at ?? (respuesta._reopened ? null : tarea.checklist?.completed_at) ?? null,
      },
    })
  }
  detalle.tasks = tareas
  return detalle
}

/**
 * Cambia el estado localmente. `markLocal` marca la OT para que el motor de
 * sincronizacion la empuje al servidor cuando vuelva la conexion.
 */
export async function updateWorkOrderStatus(workOrderId, newStatus, { markLocal = true, comment = '' } = {}) {
  if (!(await ready())) return
  await run(
    `UPDATE offline_work_orders
     SET status = ?, local_status_changed = ?, local_status_comment = ?
     WHERE id = ?`,
    [newStatus, markLocal ? 1 : 0, comment || null, workOrderId]
  )
}

/**
 * Anota una transicion hecha sin conexion. Deja la OT marcada para que
 * syncWorkOrderStatuses() la empuje al servidor al reconectar.
 */
export async function markStatusChangedOffline(workOrderId, newStatus, comment = '') {
  if (!(await ready())) return false
  // La hora es la del telefono al hacer el cambio; el servidor la acepta con
  // tolerancia (device_time). El estado de origen se conserva del primer
  // cambio sin subir: es el que tiene el servidor.
  await run(
    `UPDATE offline_work_orders
     SET local_status_from = CASE WHEN local_status_changed = 1 THEN local_status_from ELSE status END,
         local_status_changed = 1,
         local_status_comment = ?,
         local_status_at = ?,
         status = ?
     WHERE id = ?`,
    [comment || null, nowISO(), newStatus, workOrderId]
  )
  await logSync({
    entityType: 'work_order',
    entityId: workOrderId,
    action: 'transition',
    status: 'pending',
  })
  return true
}

export async function getWorkOrdersWithLocalStatusChange() {
  if (!(await ready())) return []
  return query(
    `SELECT id, status, local_status_comment, local_status_at, local_status_from
     FROM offline_work_orders
     WHERE local_status_changed = 1`
  )
}

export async function markWorkOrderStatusSynced(workOrderId) {
  if (!(await ready())) return
  await run(
    `UPDATE offline_work_orders
     SET local_status_changed = 0, local_status_comment = NULL,
         local_status_at = NULL, local_status_from = NULL
     WHERE id = ?`,
    [workOrderId]
  )
}

/**
 * El servidor rechazo un cambio de estado hecho sin red (ej. aprobar sin firma
 * guardada): la OT vuelve al estado que tiene el servidor y deja de estar en
 * cola. `estado` es ese estado si se pudo consultar; si no, el de origen
 * guardado al hacer el cambio.
 */
export async function revertRejectedStatusChange(workOrderId, estado = null) {
  if (!(await ready())) return
  await run(
    `UPDATE offline_work_orders
     SET status = COALESCE(?, local_status_from, status),
         local_status_changed = 0, local_status_comment = NULL,
         local_status_at = NULL, local_status_from = NULL
     WHERE id = ?`,
    [estado, workOrderId]
  )
}

// ── Checklists ───────────────────────────────────────────────────────────────

export async function saveChecklistResponse(response) {
  if (!(await ready()) || !response?.id) return
  // Las marcas de la lectura offline no se guardan como si vinieran del servidor.
  const { _fromOffline, _completionPending, _reopened, ...limpia } = response
  // El WHERE final: un checklist cerrado no se reabre. Varias lecturas del
  // servidor se guardan en paralelo (la consulta, el formulario, el paquete
  // offline) y una anterior al cierre puede terminar de escribirse despues:
  // pasaba al cerrar con red, y ya sin red la OT volvia a exigir ese
  // checklist para enviarla a revision. Va en la misma sentencia para que otra
  // escritura no se cuele entre la comprobacion y el guardado.
  await run(
    `INSERT OR REPLACE INTO offline_checklist_responses (
      id, work_order_id, version_id, started_at, completed_at, version_fields_json,
      task_id, response_json, local_completed_at, completion_pending,
      local_block_counts, counts_pending, local_pendientes, pendientes_pending, reopened
    ) SELECT ?,?,?,?,?,?,?,?,
      (SELECT local_completed_at FROM offline_checklist_responses WHERE id = ?),
      COALESCE((SELECT completion_pending FROM offline_checklist_responses WHERE id = ?), 0),
      (SELECT local_block_counts FROM offline_checklist_responses WHERE id = ? AND counts_pending = 1),
      COALESCE((SELECT counts_pending FROM offline_checklist_responses WHERE id = ?), 0),
      (SELECT local_pendientes FROM offline_checklist_responses WHERE id = ? AND pendientes_pending = 1),
      COALESCE((SELECT pendientes_pending FROM offline_checklist_responses WHERE id = ?), 0),
      CASE WHEN ? IS NULL THEN 0
           ELSE COALESCE((SELECT reopened FROM offline_checklist_responses WHERE id = ?), 0) END
    WHERE ? IS NOT NULL OR NOT EXISTS (
      SELECT 1 FROM offline_checklist_responses WHERE id = ? AND completed_at IS NOT NULL
    )`,
    [
      response.id,
      response.work_order ?? response.work_order_id,
      response.version ?? response.version_id ?? null,
      response.started_at ?? null,
      response.completed_at ?? null,
      JSON.stringify(response.version_fields ?? []),
      response.task ?? response.task_id ?? null,
      JSON.stringify(limpia),
      response.id,
      response.id,
      response.id,
      response.id,
      response.id,
      response.id,
      response.completed_at ?? null,
      response.id,
      response.completed_at ?? null,
      response.id,
    ]
  )
}

/**
 * Finalizar el checklist sin red: queda cerrado en el telefono y en cola para
 * el servidor. El motor de sincronizacion lo cierra despues de subir las
 * respuestas y antes de mover el estado de la OT.
 */
export async function markChecklistCompletedOffline(responseId) {
  if (!(await ready())) return
  await run(
    `UPDATE offline_checklist_responses
     SET local_completed_at = ?, completion_pending = 1
     WHERE id = ?`,
    [nowISO(), responseId]
  )
  await logSync({ entityType: 'checklist', entityId: responseId, action: 'complete', status: 'pending' })
  await run('UPDATE offline_checklist_responses SET reopened = 0 WHERE id = ?', [responseId])
}

/** Reescribe el JSON guardado de la respuesta con `cambiar(objeto)`. */
async function parchearRespuesta(responseId, cambiar) {
  const [row] = await query('SELECT response_json FROM offline_checklist_responses WHERE id = ?', [
    responseId,
  ])
  const base = parse(row?.response_json, null)
  if (!base) return
  await run('UPDATE offline_checklist_responses SET response_json = ? WHERE id = ?', [
    JSON.stringify(cambiar(base)),
    responseId,
  ])
}

/**
 * El tecnico cambio una respuesta de un checklist ya cerrado, con la OT en
 * curso: queda por cerrar de nuevo, en el telefono y (al subir la correccion)
 * en el servidor. Sin esto una lectura anterior lo volveria a dar por cerrado.
 */
export async function reopenChecklistOffline(responseId) {
  if (!(await ready())) return
  const [row] = await query(
    'SELECT completed_at, local_completed_at FROM offline_checklist_responses WHERE id = ?',
    [responseId]
  )
  if (!row || (!row.completed_at && !row.local_completed_at)) return
  await run(
    `UPDATE offline_checklist_responses
     SET completed_at = NULL, local_completed_at = NULL, completion_pending = 0, reopened = 1
     WHERE id = ?`,
    [responseId]
  )
  await parchearRespuesta(responseId, (r) => ({ ...r, completed_at: null, completed_by: null }))
}

/** El checklist se cerro con red: ya no hay nada que reabrir. */
export async function clearChecklistReopened(responseId) {
  if (!(await ready())) return
  await run('UPDATE offline_checklist_responses SET reopened = 0 WHERE id = ?', [responseId])
}

/**
 * Los pendientes ("no se pudo revisar") que dejo el tecnico, sin red. Se manda
 * la lista completa, como la recibe el servidor: reenviarla es idempotente.
 * Un checklist con pendientes no esta cerrado.
 */
export async function setPendientesOffline(responseId, lista) {
  if (!(await ready())) return
  await run(
    `UPDATE offline_checklist_responses
     SET local_pendientes = ?, pendientes_pending = 1
     WHERE id = ?`,
    [JSON.stringify(lista), responseId]
  )
  if (lista.length) await reopenChecklistOffline(responseId)
}

export async function getPendingPendientes() {
  if (!(await ready())) return []
  return query(
    'SELECT id, local_pendientes FROM offline_checklist_responses WHERE pendientes_pending = 1'
  )
}

export async function markPendientesSynced(responseId) {
  if (!(await ready())) return
  const [row] = await query(
    'SELECT local_pendientes FROM offline_checklist_responses WHERE id = ?',
    [responseId]
  )
  const subidos = parse(row?.local_pendientes, [])
  await run(
    `UPDATE offline_checklist_responses
     SET pendientes_pending = 0, local_pendientes = NULL
     WHERE id = ?`,
    [responseId]
  )
  // Lo descargado queda al dia hasta la proxima lectura del servidor.
  await parchearRespuesta(responseId, (r) => ({ ...r, pendientes: subidos }))
}

/**
 * El tecnico encontro otra cantidad de tomas sin red. Queda en el telefono y en
 * cola: el motor la sube antes que las respuestas, para que el servidor acepte
 * las de la toma nueva.
 */
export async function setBlockCountOffline(responseId, blockCounts) {
  if (!(await ready())) return
  await run(
    `UPDATE offline_checklist_responses
     SET local_block_counts = ?, counts_pending = 1
     WHERE id = ?`,
    [JSON.stringify(blockCounts), responseId]
  )
}

export async function getPendingBlockCounts() {
  if (!(await ready())) return []
  return query(
    'SELECT id, local_block_counts FROM offline_checklist_responses WHERE counts_pending = 1'
  )
}

export async function markBlockCountsSynced(responseId) {
  if (!(await ready())) return
  await run(
    `UPDATE offline_checklist_responses
     SET counts_pending = 0, local_block_counts = NULL
     WHERE id = ?`,
    [responseId]
  )
}

export async function getPendingChecklistCompletions() {
  if (!(await ready())) return []
  return query(
    'SELECT id, local_completed_at FROM offline_checklist_responses WHERE completion_pending = 1'
  )
}

export async function markChecklistCompletionSynced(responseId) {
  if (!(await ready())) return
  await run('UPDATE offline_checklist_responses SET completion_pending = 0 WHERE id = ?', [
    responseId,
  ])
}

export async function getChecklistResponse(workOrderId) {
  if (!(await ready())) return null
  const rows = await query(
    'SELECT * FROM offline_checklist_responses WHERE work_order_id = ? LIMIT 1',
    [workOrderId]
  )
  return rows[0] ?? null
}

/**
 * Guarda la respuesta a un campo. El indice unico (response_id, field_id,
 * repetition) hace que reescribir un campo reemplace la fila en vez de
 * duplicarla; en un bloque repetible, cada toma es su propia fila.
 */
export async function saveFieldResponse(fieldResponse) {
  if (!(await ready())) return
  await run(
    `INSERT INTO offline_field_responses (
      id, response_id, field_id, value, notes, answered_at, synced, repetition
    ) VALUES (?,?,?,?,?,?,?,?)
    ON CONFLICT(response_id, field_id, repetition) DO UPDATE SET
      value = excluded.value,
      notes = excluded.notes,
      answered_at = excluded.answered_at,
      synced = excluded.synced`,
    [
      fieldResponse.id ?? newId(),
      fieldResponse.response_id,
      fieldResponse.field_id,
      fieldResponse.value ?? '',
      fieldResponse.notes ?? '',
      fieldResponse.answered_at ?? nowISO(),
      fieldResponse.synced ?? 0,
      fieldResponse.repetition ?? 0,
    ]
  )
  // Si el servidor rechazo la respuesta anterior y el tecnico la corrige, la
  // nueva empieza sin historial de fallos.
  await run(
    `DELETE FROM sync_state WHERE entity_type = 'field_response' AND entity_key = (
       SELECT id FROM offline_field_responses
        WHERE response_id = ? AND field_id = ? AND repetition = ?)`,
    [fieldResponse.response_id, fieldResponse.field_id, fieldResponse.repetition ?? 0]
  )
}

export async function getUnsyncedFieldResponses(responseId = null) {
  if (!(await ready())) return []
  if (responseId) {
    return query(
      'SELECT * FROM offline_field_responses WHERE response_id = ? AND synced = 0',
      [responseId]
    )
  }
  return query('SELECT * FROM offline_field_responses WHERE synced = 0')
}

export async function markFieldResponseSynced(responseId, fieldId, repetition = 0) {
  if (!(await ready())) return
  await run(
    `UPDATE offline_field_responses SET synced = 1
     WHERE response_id = ? AND field_id = ? AND repetition = ?`,
    [responseId, fieldId, repetition ?? 0]
  )
}

// ── Fotos ────────────────────────────────────────────────────────────────────

export async function savePhotoOffline(photo) {
  if (!(await ready())) return null
  const offlineUuid = photo.offline_uuid ?? newId()
  await run(
    `INSERT OR REPLACE INTO offline_photos (
      id, work_order_id, file_path, latitude, longitude,
      taken_at, caption, file_hash, synced, offline_uuid, task_id, finding_id, stage
    ) VALUES (?,?,?,?,?,?,?,?,0,?,?,?,?)`,
    [
      photo.id ?? offlineUuid,
      photo.work_order_id,
      photo.file_path ?? null,
      photo.latitude ?? null,
      photo.longitude ?? null,
      photo.taken_at ?? nowISO(),
      photo.caption ?? null,
      photo.file_hash ?? null,
      offlineUuid,
      photo.task_id ?? null,
      photo.finding_id ?? null,
      photo.stage ?? '',
    ]
  )
  return offlineUuid
}

/**
 * Fotos sin subir, SIN la imagen (ver photoQueue.js): con decenas en cola,
 * cargarlas enteras agotaba la memoria del telefono. La imagen se pide de a
 * una con getPhotoFile().
 */
export async function getUnsyncedPhotos(workOrderId = null) {
  if (!(await ready())) return []
  return listarPendientes(driver(), workOrderId)
}

/** Cuantas fotos de la OT siguen sin subir; no lee ninguna imagen. */
export async function countUnsyncedPhotos(workOrderId) {
  if (!(await ready())) return 0
  return contarPendientes(driver(), workOrderId)
}

/** La imagen (data URL) de una foto en cola. */
export async function getPhotoFile(offlineUuid) {
  if (!(await ready())) return null
  return leerArchivo(driver(), offlineUuid)
}

export async function markPhotoSynced(offlineUuid, serverId) {
  if (!(await ready())) return
  await marcarSubida(driver(), offlineUuid, serverId)
}

// ── Firmas ───────────────────────────────────────────────────────────────────

export async function saveSignatureOffline(signature) {
  if (!(await ready())) return null
  const id = signature.id ?? newId()
  await run(
    `INSERT OR REPLACE INTO offline_signatures (
      id, work_order_id, signature_type, image_base64, signer_name,
      signer_role, latitude, longitude, signed_at, synced
    ) VALUES (?,?,?,?,?,?,?,?,?,0)`,
    [
      id,
      signature.work_order_id,
      signature.signature_type ?? null,
      signature.image_base64 ?? null,
      signature.signer_name ?? null,
      signature.signer_role ?? null,
      signature.latitude ?? null,
      signature.longitude ?? null,
      signature.signed_at ?? nowISO(),
    ]
  )
  return id
}

export async function getUnsyncedSignatures(workOrderId = null) {
  if (!(await ready())) return []
  if (workOrderId) {
    return query('SELECT * FROM offline_signatures WHERE work_order_id = ? AND synced = 0', [
      workOrderId,
    ])
  }
  return query('SELECT * FROM offline_signatures WHERE synced = 0')
}

export async function markSignatureSynced(localId, serverId) {
  if (!(await ready())) return
  await run('UPDATE offline_signatures SET synced = 1, id = ? WHERE id = ?', [
    serverId ?? localId,
    localId,
  ])
}

// ── Firma guardada del usuario ───────────────────────────────────────────────
// Copia local de su firma (data URL) para usarla sin red. Una fila por usuario.

export async function saveMySignatureLocal(userId, dataUrl) {
  if (!userId || !dataUrl || !(await ready())) return
  await run(
    'INSERT OR REPLACE INTO saved_signature (user_id, image_base64, updated_at) VALUES (?,?,?)',
    [userId, dataUrl, nowISO()]
  )
}

export async function getMySignatureLocal(userId) {
  if (!userId || !(await ready())) return null
  const [row] = await query('SELECT image_base64 FROM saved_signature WHERE user_id = ?', [userId])
  return row?.image_base64 ?? null
}

export async function clearMySignatureLocal(userId) {
  if (!userId || !(await ready())) return
  await run('DELETE FROM saved_signature WHERE user_id = ?', [userId])
}

// ── Estado de sincronizacion ─────────────────────────────────────────────────

/** Cuantos elementos hay pendientes de subir, en total. */
export async function countPendingSync() {
  if (!(await ready())) return 0
  const rows = await query(
    `SELECT
       (SELECT COUNT(*) FROM offline_field_responses WHERE synced = 0) +
       (SELECT COUNT(*) FROM offline_photos WHERE synced = 0) +
       (SELECT COUNT(*) FROM offline_signatures WHERE synced = 0) +
       (SELECT COUNT(*) FROM offline_checklist_responses WHERE completion_pending = 1) +
       (SELECT COUNT(*) FROM offline_checklist_responses WHERE counts_pending = 1) +
       (SELECT COUNT(*) FROM offline_checklist_responses WHERE pendientes_pending = 1) +
       (SELECT COUNT(*) FROM offline_findings WHERE pending_action IS NOT NULL) +
       (SELECT COUNT(*) FROM offline_work_orders WHERE local_status_changed = 1)
     AS total`
  )
  return rows[0]?.total ?? 0
}

/** Ids de OT que tienen algo sin sincronizar, para el punto naranja de la tarjeta. */
export async function getWorkOrderIdsWithPendingSync() {
  if (!(await ready())) return []
  const rows = await query(
    `SELECT DISTINCT work_order_id AS id FROM offline_photos WHERE synced = 0
     UNION
     SELECT DISTINCT work_order_id AS id FROM offline_signatures WHERE synced = 0
     UNION
     SELECT DISTINCT r.work_order_id AS id
       FROM offline_field_responses f
       JOIN offline_checklist_responses r ON r.id = f.response_id
      WHERE f.synced = 0
     UNION
     SELECT DISTINCT work_order_id AS id FROM offline_checklist_responses
      WHERE completion_pending = 1 OR pendientes_pending = 1
     UNION
     SELECT id FROM offline_work_orders WHERE local_status_changed = 1
     UNION
     SELECT DISTINCT work_order_id AS id FROM offline_findings WHERE pending_action IS NOT NULL`
  )
  return rows.map((r) => r.id).filter(Boolean)
}

export async function logSync({ entityType, entityId, action, status, errorMessage = null }) {
  if (!(await ready())) return
  await run(
    `INSERT INTO sync_log (entity_type, entity_id, action, status, error_message, attempted_at)
     VALUES (?,?,?,?,?,?)`,
    [entityType, entityId, action, status, errorMessage, nowISO()]
  )
}

export async function getSyncLog(limit = 50) {
  if (!(await ready())) return []
  return query('SELECT * FROM sync_log ORDER BY id DESC LIMIT ?', [limit])
}

// ── Reintentos por elemento ──────────────────────────────────────────────────
//
// sync_state guarda, por elemento en cola, cuantas veces fallo y que sigue:
// 'retry' (reintento automatico desde next_retry_at) o 'attention' (el servidor
// lo rechazo y espera al tecnico). Sin fila = nunca ha fallado. La politica
// (que es transitorio, cuanto se espera) vive en sync/retryPolicy.js.

const stateKey = (entityType, entityKey) => `${entityType}:${entityKey}`

/** Todos los estados, indexados por "tipo:id". */
export async function getSyncStates() {
  if (!(await ready())) return new Map()
  const rows = await query('SELECT * FROM sync_state')
  return new Map(rows.map((r) => [stateKey(r.entity_type, r.entity_key), r]))
}

/** work_order_id de cada checklist, para ubicar sus respuestas y su cierre. */
export async function getChecklistWorkOrderIds() {
  if (!(await ready())) return new Map()
  const rows = await query('SELECT id, work_order_id FROM offline_checklist_responses')
  return new Map(rows.map((r) => [r.id, r.work_order_id]))
}

/** Anota un fallo. `state` es lo que devuelve nextState() de retryPolicy. */
export async function saveSyncFailure({ entityType, entityKey, workOrderId = null, state, message }) {
  if (!(await ready())) return
  const now = nowISO()
  await run(
    `INSERT INTO sync_state (
       entity_type, entity_key, work_order_id, status, attempts, next_retry_at,
       http_status, error_message, first_failed_at, updated_at
     ) VALUES (?,?,?,?,?,?,?,?,?,?)
     ON CONFLICT(entity_type, entity_key) DO UPDATE SET
       work_order_id = COALESCE(excluded.work_order_id, work_order_id),
       status = excluded.status,
       attempts = excluded.attempts,
       next_retry_at = excluded.next_retry_at,
       http_status = excluded.http_status,
       error_message = excluded.error_message,
       updated_at = excluded.updated_at`,
    [
      entityType, entityKey, workOrderId, state.status, state.attempts,
      state.next_retry_at, state.http_status, message, now, now,
    ]
  )
}

/** El elemento subio (o ya no hace falta): se olvida su historial de fallos. */
export async function clearSyncState(entityType, entityKey) {
  if (!(await ready())) return
  await run('DELETE FROM sync_state WHERE entity_type = ? AND entity_key = ?', [entityType, entityKey])
}

/** Elementos que el servidor rechazo, con la OT a la que pertenecen. */
export async function getAttentionItems() {
  if (!(await ready())) return []
  return query(
    `SELECT s.entity_type, s.entity_key, s.work_order_id, s.http_status,
            s.error_message, s.attempts, s.updated_at,
            wo.wo_number, wo.title AS wo_title
       FROM sync_state s
       LEFT JOIN offline_work_orders wo ON wo.id = s.work_order_id
      WHERE s.status = 'attention'
      ORDER BY s.updated_at`
  )
}

/**
 * "Reintentar": el elemento vuelve a la cola como nuevo (sin espera y con los
 * intentos en cero). Sin `keys` reencola todos los que requieren atencion.
 * `keys` son pares { entity_type, entity_key }.
 */
export async function requeueAttentionItems(keys = null) {
  if (!(await ready())) return
  if (!keys) {
    await run("DELETE FROM sync_state WHERE status = 'attention'")
    return
  }
  for (const k of keys) {
    await run(
      "DELETE FROM sync_state WHERE status = 'attention' AND entity_type = ? AND entity_key = ?",
      [k.entity_type, k.entity_key]
    )
  }
}

/** Volvio la red: lo que esperaba su turno se intenta ya, sin esperar el backoff. */
export async function clearBackoff() {
  if (!(await ready())) return
  await run("UPDATE sync_state SET next_retry_at = NULL WHERE status = 'retry'")
}

// ── Hallazgos (bloque E) ─────────────────────────────────────────────────────
//
// Cada fila guarda el hallazgo con la forma de la API (data_json) y su cola:
// pending_action 'save' (crear o corregir) o 'delete'. El id lo pone el
// telefono: sus fotos lo referencian antes de sincronizar, y reenviar el alta
// no lo duplica en el servidor.

const SEVERIDAD = { LOW: 'Baja', MEDIUM: 'Media', HIGH: 'Alta', CRITICAL: 'Crítica' }

/**
 * Lo que trae el servidor. No pisa lo que el tecnico cambio sin red y aun no
 * sube; lo que el servidor ya no tiene (y aqui no esta en cola) se quita.
 */
export async function saveFindingsFromServer(workOrderId, findings = []) {
  if (!(await ready())) return
  const ids = findings.map((f) => f.id)
  for (const f of findings) {
    await run(
      `INSERT INTO offline_findings (id, work_order_id, data_json, pending_action, server_known, updated_at)
       VALUES (?, ?, ?, NULL, 1, ?)
       ON CONFLICT(id) DO UPDATE SET
         data_json = CASE WHEN offline_findings.pending_action IS NULL THEN excluded.data_json
                          ELSE offline_findings.data_json END,
         server_known = 1`,
      [f.id, workOrderId, JSON.stringify(f), nowISO()]
    )
  }
  const marcas = ids.map(() => '?').join(',')
  await run(
    `DELETE FROM offline_findings
      WHERE work_order_id = ? AND pending_action IS NULL
        ${ids.length ? `AND id NOT IN (${marcas})` : ''}`,
    [workOrderId, ...ids]
  )
}

/** Los hallazgos de la OT como los devolveria la API, con lo hecho sin red. */
export async function getOfflineFindings(workOrderId) {
  if (!(await ready())) return []
  const rows = await query(
    `SELECT f.*, (SELECT COUNT(*) FROM offline_photos p WHERE p.finding_id = f.id AND p.synced = 0)
              AS fotos_en_cola
       FROM offline_findings f
      WHERE f.work_order_id = ? AND COALESCE(f.pending_action, '') != 'delete'
      ORDER BY f.updated_at`,
    [workOrderId]
  )
  return rows.map((r) => {
    const f = JSON.parse(r.data_json)
    return {
      ...f,
      photos_count: (f.photos_count ?? 0) + (r.fotos_en_cola ?? 0),
      _pending: r.pending_action != null,
    }
  })
}

/** Alta o correccion sin red: queda en cola. */
export async function saveFindingOffline(finding) {
  if (!(await ready())) return null
  const [previa] = await query('SELECT data_json FROM offline_findings WHERE id = ?', [finding.id])
  const antes = previa ? JSON.parse(previa.data_json) : {}
  const datos = {
    ...antes,
    ...finding,
    severity_display: SEVERIDAD[finding.severity ?? antes.severity],
    status: (finding.resolved_on_site ?? antes.resolved_on_site) ? 'RESOLVED' : 'PENDING',
    status_display: (finding.resolved_on_site ?? antes.resolved_on_site) ? 'Resuelto en sitio' : 'Pendiente',
  }
  await run(
    `INSERT INTO offline_findings (id, work_order_id, data_json, pending_action, server_known, updated_at)
     VALUES (?, ?, ?, 'save', 0, ?)
     ON CONFLICT(id) DO UPDATE SET data_json = excluded.data_json, pending_action = 'save'`,
    [datos.id, datos.work_order, JSON.stringify(datos), nowISO()]
  )
  await clearSyncState('finding', datos.id)
  return datos
}

/**
 * Quitar sin red. Si el servidor nunca lo tuvo, basta con olvidarlo aqui (y
 * sus fotos en cola quedan como evidencia de la OT, sin hallazgo, igual que
 * en el servidor); si ya lo tiene, se le pide borrarlo al reconectar.
 */
export async function deleteFindingOffline(id) {
  if (!(await ready())) return
  const [fila] = await query('SELECT server_known FROM offline_findings WHERE id = ?', [id])
  if (!fila) return
  await run('UPDATE offline_photos SET finding_id = NULL WHERE finding_id = ?', [id])
  if (fila.server_known) {
    await run("UPDATE offline_findings SET pending_action = 'delete' WHERE id = ?", [id])
  } else {
    await run('DELETE FROM offline_findings WHERE id = ?', [id])
  }
}

export async function getPendingFindings() {
  if (!(await ready())) return []
  return query(
    'SELECT * FROM offline_findings WHERE pending_action IS NOT NULL ORDER BY updated_at'
  )
}

export async function markFindingSynced(id, serverFinding = null) {
  if (!(await ready())) return
  if (serverFinding === null) {
    await run('DELETE FROM offline_findings WHERE id = ?', [id])
    return
  }
  await run(
    'UPDATE offline_findings SET pending_action = NULL, server_known = 1, data_json = ? WHERE id = ?',
    [JSON.stringify(serverFinding), id]
  )
}
