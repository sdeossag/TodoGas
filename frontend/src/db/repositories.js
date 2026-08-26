/**
 * Acceso a la base offline. Todo el SQL vive aqui; el resto de la app habla
 * con estas funciones y nunca con la conexion directamente.
 *
 * Cuando SQLite no esta disponible (navegador sin soporte) las lecturas
 * devuelven vacio y las escrituras son no-op, sin lanzar.
 */

import { query, ready, run } from './database'
import { PRIORITY_RANK_SQL } from './schema'

const nowISO = () => new Date().toISOString()

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
          local_status_changed, local_status_comment
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
          COALESCE((SELECT local_status_changed FROM offline_work_orders WHERE id = ?), 0),
          (SELECT local_status_comment FROM offline_work_orders WHERE id = ?)
        )`,
        [
          wo.id,
          wo.wo_number ?? null,
          wo.title ?? null,
          wo.description ?? null,
          wo.task_type ?? null,
          wo.status ?? null,
          wo.priority ?? null,
          wo.scheduled_date ?? null,
          wo.asset?.id ?? null,
          wo.asset?.name ?? null,
          wo.asset?.code ?? null,
          wo.hospital?.name ?? wo.asset?.hospital?.name ?? null,
          wo.hospital?.id ?? wo.asset?.hospital?.id ?? null,
          wo.assigned_to?.id ?? wo.assigned_to ?? null,
          wo.checklist_version?.id ?? wo.checklist_version_id ?? null,
          wo.checklist_response?.id ?? wo.checklist_response_id ?? null,
          wo.notes ?? null,
          nowISO(),
          wo.id, // offline_uuid: para las que vienen del servidor basta el id
          JSON.stringify(wo),
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
  await run(
    `UPDATE offline_work_orders
     SET local_status_changed = 1,
         local_status_comment = ?,
         status = ?
     WHERE id = ?`,
    [comment || null, newStatus, workOrderId]
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
    `SELECT id, status, local_status_comment
     FROM offline_work_orders
     WHERE local_status_changed = 1`
  )
}

export async function markWorkOrderStatusSynced(workOrderId) {
  if (!(await ready())) return
  await run(
    `UPDATE offline_work_orders
     SET local_status_changed = 0, local_status_comment = NULL
     WHERE id = ?`,
    [workOrderId]
  )
}

// ── Checklists ───────────────────────────────────────────────────────────────

export async function saveChecklistResponse(response) {
  if (!(await ready()) || !response?.id) return
  await run(
    `INSERT OR REPLACE INTO offline_checklist_responses (
      id, work_order_id, version_id, started_at, completed_at, version_fields_json
    ) VALUES (?,?,?,?,?,?)`,
    [
      response.id,
      response.work_order ?? response.work_order_id,
      response.version ?? response.version_id ?? null,
      response.started_at ?? null,
      response.completed_at ?? null,
      JSON.stringify(response.version_fields ?? []),
    ]
  )
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
 * Guarda la respuesta a un campo. El indice unico (response_id, field_id)
 * hace que reescribir un campo reemplace la fila en vez de duplicarla.
 */
export async function saveFieldResponse(fieldResponse) {
  if (!(await ready())) return
  await run(
    `INSERT INTO offline_field_responses (
      id, response_id, field_id, value, notes, answered_at, synced
    ) VALUES (?,?,?,?,?,?,?)
    ON CONFLICT(response_id, field_id) DO UPDATE SET
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
    ]
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

export async function markFieldResponseSynced(responseId, fieldId) {
  if (!(await ready())) return
  await run(
    'UPDATE offline_field_responses SET synced = 1 WHERE response_id = ? AND field_id = ?',
    [responseId, fieldId]
  )
}

// ── Fotos ────────────────────────────────────────────────────────────────────

export async function savePhotoOffline(photo) {
  if (!(await ready())) return null
  const offlineUuid = photo.offline_uuid ?? newId()
  await run(
    `INSERT OR REPLACE INTO offline_photos (
      id, work_order_id, file_path, latitude, longitude,
      taken_at, caption, file_hash, synced, offline_uuid
    ) VALUES (?,?,?,?,?,?,?,?,0,?)`,
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
    ]
  )
  return offlineUuid
}

export async function getUnsyncedPhotos(workOrderId = null) {
  if (!(await ready())) return []
  if (workOrderId) {
    return query('SELECT * FROM offline_photos WHERE work_order_id = ? AND synced = 0', [
      workOrderId,
    ])
  }
  return query('SELECT * FROM offline_photos WHERE synced = 0')
}

export async function markPhotoSynced(offlineUuid, serverId) {
  if (!(await ready())) return
  await run('UPDATE offline_photos SET synced = 1, id = ? WHERE offline_uuid = ?', [
    serverId,
    offlineUuid,
  ])
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

// ── Estado de sincronizacion ─────────────────────────────────────────────────

/** Cuantos elementos hay pendientes de subir, en total. */
export async function countPendingSync() {
  if (!(await ready())) return 0
  const rows = await query(
    `SELECT
       (SELECT COUNT(*) FROM offline_field_responses WHERE synced = 0) +
       (SELECT COUNT(*) FROM offline_photos WHERE synced = 0) +
       (SELECT COUNT(*) FROM offline_signatures WHERE synced = 0) +
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
     SELECT id FROM offline_work_orders WHERE local_status_changed = 1`
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
