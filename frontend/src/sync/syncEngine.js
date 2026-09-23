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
  getPendingBlockCounts,
  getPendingChecklistCompletions,
  getUnsyncedFieldResponses,
  getPendingFindings,
  getUnsyncedPhotos,
  markFindingSynced,
  getUnsyncedSignatures,
  getWorkOrdersWithLocalStatusChange,
  logSync,
  markBlockCountsSynced,
  markChecklistCompletionSynced,
  markFieldResponseSynced,
  markPhotoSynced,
  markSignatureSynced,
  markWorkOrderStatusSynced,
} from '../db/repositories'

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

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
        repetition: row.repetition ?? 0,
        value: row.value ?? '',
        notes: row.notes ?? '',
        // La hora en que se respondio aqui, no la de sincronizar: es la del acta.
        answered_at: row.answered_at ?? null,
      })
      await markFieldResponseSynced(row.response_id, row.field_id, row.repetition ?? 0)
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
      await client.post(`/api/checklists/responses/${row.id}/complete/`, {
        completed_at: row.local_completed_at ?? null,
      })
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

/**
 * Hallazgos creados, corregidos o quitados sin red. Van antes que las fotos
 * (una foto referencia su hallazgo) y antes del estado de la OT (enviada a
 * revision ya no se aceptan cambios). El alta manda el id del telefono: si la
 * respuesta se perdio, reenviarla devuelve el mismo hallazgo.
 */
export async function syncFindings(onItemDone) {
  const pending = await getPendingFindings()
  let ok = 0
  let failed = 0

  for (const row of pending) {
    const f = JSON.parse(row.data_json)
    try {
      if (row.pending_action === 'delete') {
        try {
          await client.delete(`/api/findings/${row.id}/`)
        } catch (error) {
          // Ya no estaba: lo que se queria, que no este.
          if (error?.response?.status !== 404) throw error
        }
        await markFindingSynced(row.id, null)
      } else {
        const datos = {
          asset: f.asset,
          description: f.description,
          severity: f.severity,
          out_of_service: !!f.out_of_service,
          resolved_on_site: !!f.resolved_on_site,
          resolution_notes: f.resolution_notes ?? '',
        }
        let respuesta = row.server_known
          ? await client.patch(`/api/findings/${row.id}/`, datos)
          : await client.post('/api/findings/', {
              ...datos, id: row.id, work_order: row.work_order_id, reported_at: f.reported_at,
            })
        // 200 al alta: ya habia llegado (se perdio la respuesta). Lo corregido
        // despues sin red va como correccion.
        if (!row.server_known && respuesta.status === 200) {
          respuesta = await client.patch(`/api/findings/${row.id}/`, datos)
        }
        await markFindingSynced(row.id, respuesta.data)
      }
      await logSync({ entityType: 'finding', entityId: row.id, action: row.pending_action, status: 'ok' })
      ok += 1
    } catch (error) {
      await logSync({
        entityType: 'finding',
        entityId: row.id,
        action: row.pending_action,
        status: 'error',
        errorMessage: errorText(error),
      })
      failed += 1
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
      // Foto de un hallazgo: el hallazgo ya subio (syncFindings va antes).
      if (row.finding_id) form.append('finding', row.finding_id)
      form.append('file', file)
      if (row.latitude != null) form.append('latitude', row.latitude)
      if (row.longitude != null) form.append('longitude', row.longitude)
      form.append('taken_at', row.taken_at)
      if (row.caption) form.append('caption', row.caption)
      // Con el identificador del telefono un reintento no duplica la foto, y el
      // campo foto del checklist ('sin-conexion:<uuid>') la encuentra despues.
      // Sin crypto.randomUUID newId() da 'local-...', que el servidor
      // rechazaria junto con la foto: ese no se manda.
      if (UUID.test(row.offline_uuid ?? '')) form.append('offline_uuid', row.offline_uuid)

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
        signed_at: row.signed_at ?? null,
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

/**
 * Cantidades de tomas ajustadas sin red. Van antes que las respuestas: el
 * servidor rechaza la toma 21 mientras siga creyendo que hay 20.
 */
export async function syncBlockCounts(onItemDone) {
  const pending = await getPendingBlockCounts()
  let ok = 0
  let failed = 0

  for (const row of pending) {
    let cuantas = {}
    try {
      cuantas = JSON.parse(row.local_block_counts ?? '{}')
    } catch {
      cuantas = {}
    }
    try {
      for (const [group, count] of Object.entries(cuantas)) {
        await client.post(`/api/checklists/responses/${row.id}/block-count/`, { group, count })
      }
      await markBlockCountsSynced(row.id)
      ok += 1
    } catch (error) {
      // Un checklist que ya se cerro en el servidor no admite cambios: no hay
      // nada que reintentar.
      if (error?.response?.status === 400 && /completado/i.test(errorText(error))) {
        await markBlockCountsSynced(row.id)
        ok += 1
      } else {
        failed += 1
        await logSync({
          entityType: 'checklist',
          entityId: row.id,
          action: 'block-count',
          status: 'error',
          errorMessage: errorText(error),
        })
      }
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

  // El orden es deliberado: cantidad de tomas, respuestas, cierre de cada
  // checklist, hallazgos (antes que las fotos que los referencian), evidencia
  // y al final el estado de la OT, que valida todo lo anterior.
  const counts = await syncBlockCounts(tick)
  const fields = await syncFieldResponses(tick)
  const checklists = await syncChecklistCompletions(tick)
  const findings = await syncFindings(tick)
  const photos = await syncPhotos(tick)
  const signatures = await syncSignatures(tick)
  const workOrders = await syncWorkOrderStatuses(tick)

  const result = { counts, fields, checklists, findings, photos, signatures, workOrders }
  const fases = Object.values(result)
  const failed = fases.reduce((acc, f) => acc + f.failed, 0)
  const synced = fases.reduce((acc, f) => acc + f.ok, 0)

  onProgress?.(await countPendingSync())

  if (synced || failed) {
    console.info(`[sync] ${synced} elementos subidos, ${failed} con error`, result)
  }
  return result
}
