/**
 * Motor de sincronizacion offline.
 *
 * El orden de las fases importa: las respuestas del checklist y la evidencia
 * tienen que estar en el servidor antes de mover el estado de la OT, porque
 * una transicion a COMPLETED valida que el checklist este completo.
 *
 * Ningun fallo individual aborta la tanda: cada error se anota en sync_log y
 * el elemento se reintenta en la siguiente pasada.
 */

import client from '../api/client'
import {
  countPendingSync,
  getPendingChecklistCompletions,
  getUnsyncedFieldResponses,
  getUnsyncedPhotos,
  getUnsyncedSignatures,
  getWorkOrdersWithLocalStatusChange,
  logSync,
  markChecklistCompletionSynced,
  markFieldResponseSynced,
  markPhotoSynced,
  markSignatureSynced,
  markWorkOrderStatusSynced,
} from '../db/repositories'

const errorText = (error) => {
  const data = error?.response?.data
  if (typeof data === 'string') return data.slice(0, 300)
  if (data) return JSON.stringify(data).slice(0, 300)
  return error?.message ?? 'Error desconocido'
}

/** Convierte una data URL en File para poder subirla como multipart. */
async function dataUrlToFile(dataUrl, filename) {
  const response = await fetch(dataUrl)
  const blob = await response.blob()
  const ext = (blob.type.split('/')[1] ?? 'jpg').replace('jpeg', 'jpg')
  return new File([blob], `${filename}.${ext}`, { type: blob.type || 'image/jpeg' })
}

// ── Fases ────────────────────────────────────────────────────────────────────

export async function syncFieldResponses(onItemDone) {
  const pending = await getUnsyncedFieldResponses()
  let ok = 0
  let failed = 0

  for (const row of pending) {
    try {
      await client.post(`/api/checklists/responses/${row.response_id}/submit-field/`, {
        field: row.field_id,
        value: row.value ?? '',
        notes: row.notes ?? '',
      })
      await markFieldResponseSynced(row.response_id, row.field_id)
      await logSync({
        entityType: 'field_response',
        entityId: row.id,
        action: 'submit-field',
        status: 'ok',
      })
      ok += 1
    } catch (error) {
      await logSync({
        entityType: 'field_response',
        entityId: row.id,
        action: 'submit-field',
        status: 'error',
        errorMessage: errorText(error),
      })
      failed += 1
    }
    onItemDone?.()
  }

  return { ok, failed, total: pending.length }
}

/**
 * Checklists finalizados sin red. Van despues de las respuestas (el servidor
 * rechaza cerrar uno con obligatorios sin responder) y antes del estado de la
 * OT (pasar a revision exige todos los checklists cerrados).
 */
export async function syncChecklistCompletions(onItemDone) {
  const pending = await getPendingChecklistCompletions()
  let ok = 0
  let failed = 0

  for (const row of pending) {
    try {
      await client.post(`/api/checklists/responses/${row.id}/complete/`)
      await markChecklistCompletionSynced(row.id)
      await logSync({ entityType: 'checklist', entityId: row.id, action: 'complete', status: 'ok' })
      ok += 1
    } catch (error) {
      // Si ya estaba cerrado en el servidor (se cerro desde otra sesion), el
      // cierre en cola ya no tiene nada que hacer.
      if (error?.response?.status === 400 && /ya est. completado/i.test(error.response.data?.detail ?? '')) {
        await markChecklistCompletionSynced(row.id)
        ok += 1
      } else {
        await logSync({
          entityType: 'checklist',
          entityId: row.id,
          action: 'complete',
          status: 'error',
          errorMessage: errorText(error),
        })
        failed += 1
      }
    }
    onItemDone?.()
  }

  return { ok, failed, total: pending.length }
}

export async function syncPhotos(onItemDone) {
  const pending = await getUnsyncedPhotos()
  let ok = 0
  let failed = 0

  for (const row of pending) {
    try {
      if (!row.file_path?.startsWith('data:')) {
        // La camara nativa guarda base64 como data URL, igual que el flujo web.
        // Cualquier otra cosa es una fila corrupta y no se puede subir.
        throw new Error(`Ruta de foto no soportada: ${row.file_path ?? 'vacia'}`)
      }

      const file = await dataUrlToFile(row.file_path, `ot-${row.work_order_id}`)
      const form = new FormData()
      form.append('work_order', row.work_order_id)
      if (row.task_id) form.append('task', row.task_id)
      form.append('file', file)
      if (row.latitude != null) form.append('latitude', row.latitude)
      if (row.longitude != null) form.append('longitude', row.longitude)
      form.append('taken_at', row.taken_at)
      if (row.caption) form.append('caption', row.caption)

      const { data } = await client.post('/api/evidence/photos/', form, {
        headers: { 'Content-Type': undefined },
      })

      await markPhotoSynced(row.offline_uuid, data.id)
      await logSync({
        entityType: 'photo',
        entityId: row.offline_uuid,
        action: 'upload',
        status: 'ok',
      })
      ok += 1
    } catch (error) {
      await logSync({
        entityType: 'photo',
        entityId: row.offline_uuid,
        action: 'upload',
        status: 'error',
        errorMessage: errorText(error),
      })
      failed += 1
    }
    onItemDone?.()
  }

  return { ok, failed, total: pending.length }
}

export async function syncSignatures(onItemDone) {
  const pending = await getUnsyncedSignatures()
  let ok = 0
  let failed = 0

  for (const row of pending) {
    try {
      const { data } = await client.post('/api/evidence/signatures/', {
        work_order: row.work_order_id,
        image_data: (row.image_base64 ?? '').replace(/^data:image\/\w+;base64,/, ''),
        signer_name: row.signer_name,
        signer_role: row.signer_role,
        // Sin esto el backend cae al default TECHNICIAN y una firma de
        // cliente capturada sin conexion se subiria con el tipo equivocado.
        ...(row.signature_type ? { signature_type: row.signature_type } : {}),
      })
      await markSignatureSynced(row.id, data.id)
      await logSync({
        entityType: 'signature',
        entityId: row.id,
        action: 'upload',
        status: 'ok',
      })
      ok += 1
    } catch (error) {
      await logSync({
        entityType: 'signature',
        entityId: row.id,
        action: 'upload',
        status: 'error',
        errorMessage: errorText(error),
      })
      failed += 1
    }
    onItemDone?.()
  }

  return { ok, failed, total: pending.length }
}

export async function syncWorkOrderStatuses(onItemDone) {
  const pending = await getWorkOrdersWithLocalStatusChange()
  let ok = 0
  let failed = 0

  for (const row of pending) {
    try {
      await client.post(`/api/work-orders/${row.id}/transition/`, {
        new_status: row.status,
        comment: row.local_status_comment ?? 'Cambio realizado sin conexion',
      })
      await markWorkOrderStatusSynced(row.id)
      await logSync({
        entityType: 'work_order',
        entityId: row.id,
        action: 'transition',
        status: 'ok',
      })
      ok += 1
    } catch (error) {
      await logSync({
        entityType: 'work_order',
        entityId: row.id,
        action: 'transition',
        status: 'error',
        errorMessage: errorText(error),
      })
      failed += 1
    }
    onItemDone?.()
  }

  return { ok, failed, total: pending.length }
}

// ── Orquestador ──────────────────────────────────────────────────────────────

/**
 * Sube todo lo pendiente. Se llama al recuperar conexion.
 *
 * onProgress recibe cuantos elementos quedan por subir, para el banner.
 */
export async function syncOfflineData({ onProgress } = {}) {
  let remaining = await countPendingSync()
  onProgress?.(remaining)

  const tick = () => {
    remaining = Math.max(0, remaining - 1)
    onProgress?.(remaining)
  }

  // El orden es deliberado: respuestas, cierre de cada checklist, evidencia
  // y al final el estado de la OT, que valida todo lo anterior.
  const fields = await syncFieldResponses(tick)
  const checklists = await syncChecklistCompletions(tick)
  const photos = await syncPhotos(tick)
  const signatures = await syncSignatures(tick)
  const workOrders = await syncWorkOrderStatuses(tick)

  const result = { fields, checklists, photos, signatures, workOrders }
  const fases = Object.values(result)
  const failed = fases.reduce((acc, f) => acc + f.failed, 0)
  const synced = fases.reduce((acc, f) => acc + f.ok, 0)

  onProgress?.(await countPendingSync())

  if (synced || failed) {
    console.info(`[sync] ${synced} elementos subidos, ${failed} con error`, result)
  }
  return result
}
