/**
 * Motor de sincronizacion offline.
 *
 * El orden de las fases importa: las respuestas del checklist y la evidencia
 * tienen que estar en el servidor antes de mover el estado de la OT, porque
 * una transicion a COMPLETED valida que el checklist este completo.
 *
 * Ningun fallo individual aborta la tanda: cada error se anota en sync_log y
 * en sync_state. Segun el error (ver retryPolicy.js) el elemento se reintenta
 * con espera creciente, o pasa a "requiere atencion" y no se vuelve a mandar
 * solo: nunca se descarta, es evidencia.
 *
 * Dependencias: si un elemento no sube en esta pasada (fallo, espera o
 * atencion), lo que depende de el se salta sin intentarse y sin anotarle un
 * fallo: el servidor lo rechazaria por culpa del padre, no por culpa suya.
 */

import client from '../api/client'
import {
  countPendingSync,
  getPendingBlockCounts,
  getPendingChecklistCompletions,
  getPendingPendientes,
  markPendientesSynced,
  getUnsyncedFieldResponses,
  getPendingFindings,
  getPhotoFile,
  getUnsyncedPhotos,
  markFindingSynced,
  getUnsyncedSignatures,
  getWorkOrdersWithLocalStatusChange,
  getChecklistWorkOrderIds,
  getSyncStates,
  clearSyncState,
  saveSyncFailure,
  logSync,
  markBlockCountsSynced,
  markChecklistCompletionSynced,
  markFieldResponseSynced,
  markPhotoSynced,
  markSignatureSynced,
  markWorkOrderStatusSynced,
  revertRejectedStatusChange,
} from '../db/repositories'
import { dueNow, esRechazoDeTransicion, isChecklistCompleted, nextState, serverMessage } from './retryPolicy'

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

/**
 * Intenta un elemento respetando su estado de reintentos y las dependencias.
 * Devuelve 'ok', 'failed' (fallo nuevo), 'waiting' (en espera o requiere
 * atencion) o 'blocked' (su padre no subio).
 *
 *   ctx      { estados, ahora } de la pasada
 *   item     { type, key, workOrderId, log: {entityType, entityId, action} }
 *   bloqueado  true si algo de lo que depende no subio
 *   alNoSubir  se llama si este elemento no sube, para bloquear a sus dependientes
 *   fn       la subida; lanza si falla
 */
async function intentar(ctx, item, { bloqueado = false, alNoSubir, logOk = true }, fn) {
  if (bloqueado) {
    alNoSubir?.()
    return 'blocked'
  }
  const estado = ctx.estados.get(`${item.type}:${item.key}`)
  if (!dueNow(estado, ctx.ahora)) {
    alNoSubir?.()
    return 'waiting'
  }
  try {
    await fn()
    if (estado) await clearSyncState(item.type, item.key)
    if (logOk) await logSync({ ...item.log, status: 'ok' })
    return 'ok'
  } catch (error) {
    await logSync({ ...item.log, status: 'error', errorMessage: errorText(error) })
    await saveSyncFailure({
      entityType: item.type,
      entityKey: item.key,
      workOrderId: item.workOrderId ?? null,
      state: nextState(estado, error, ctx.ahora),
      message: serverMessage(error),
    })
    alNoSubir?.()
    return 'failed'
  }
}

/** Cuenta el resultado de un elemento en el resumen de la fase. */
function contar(resumen, resultado) {
  if (resultado === 'ok') resumen.ok += 1
  else if (resultado === 'failed') resumen.failed += 1
  else resumen.waiting += 1
}

const resumenVacio = (total) => ({ ok: 0, failed: 0, waiting: 0, total })

/** Contexto de una pasada: estados de reintento y lo que quedo sin subir. */
async function nuevoContexto() {
  return {
    estados: await getSyncStates(),
    ahora: Date.now(),
    checklistOT: await getChecklistWorkOrderIds(),
    // Lo que no subio en esta pasada y bloquea a sus dependientes.
    sinCantidad: new Set(), // checklists con la cantidad de tomas sin subir
    sinRespuestas: new Set(), // checklists con alguna respuesta sin subir
    sinPendientes: new Set(), // checklists con la lista de pendientes sin subir
    sinHallazgo: new Set(), // hallazgos sin subir (sus fotos esperan)
    sinSubir: new Set(), // OT con algo sin subir (su cambio de estado espera)
  }
}

// ── Fases ────────────────────────────────────────────────────────────────────

/**
 * Cantidad de tomas ajustadas sin red. Van antes que las respuestas: el
 * servidor rechaza la toma 21 mientras siga creyendo que hay 20.
 */
export async function syncBlockCounts(ctx, onItemDone) {
  const pending = await getPendingBlockCounts()
  const resumen = resumenVacio(pending.length)

  for (const row of pending) {
    const workOrderId = ctx.checklistOT.get(row.id)
    let cuantas = {}
    try {
      cuantas = JSON.parse(row.local_block_counts ?? '{}')
    } catch {
      cuantas = {}
    }
    const resultado = await intentar(
      ctx,
      {
        type: 'block_count',
        key: row.id,
        workOrderId,
        log: { entityType: 'checklist', entityId: row.id, action: 'block-count' },
      },
      {
        logOk: false,
        alNoSubir: () => {
          ctx.sinCantidad.add(row.id)
          ctx.sinSubir.add(workOrderId)
        },
      },
      async () => {
        try {
          for (const [group, count] of Object.entries(cuantas)) {
            await client.post(`/api/checklists/responses/${row.id}/block-count/`, { group, count })
          }
        } catch (error) {
          // Un checklist que ya se cerro en el servidor no admite cambios: no
          // hay nada que reintentar.
          if (!isChecklistCompleted(error)) throw error
        }
        await markBlockCountsSynced(row.id)
      }
    )
    contar(resumen, resultado)
    onItemDone?.()
  }
  return resumen
}

export async function syncFieldResponses(ctx, onItemDone) {
  const pending = await getUnsyncedFieldResponses()
  const resumen = resumenVacio(pending.length)

  for (const row of pending) {
    const workOrderId = ctx.checklistOT.get(row.response_id)
    const resultado = await intentar(
      ctx,
      {
        type: 'field_response',
        key: row.id,
        workOrderId,
        log: { entityType: 'field_response', entityId: row.id, action: 'submit-field' },
      },
      {
        bloqueado: ctx.sinCantidad.has(row.response_id),
        alNoSubir: () => {
          ctx.sinRespuestas.add(row.response_id)
          ctx.sinSubir.add(workOrderId)
        },
      },
      async () => {
        await client.post(`/api/checklists/responses/${row.response_id}/submit-field/`, {
          field: row.field_id,
          repetition: row.repetition ?? 0,
          value: row.value ?? '',
          notes: row.notes ?? '',
          // La hora en que se respondio aqui, no la de sincronizar: es la del acta.
          answered_at: row.answered_at ?? null,
        })
        await markFieldResponseSynced(row.response_id, row.field_id, row.repetition ?? 0)
      }
    )
    contar(resumen, resultado)
    onItemDone?.()
  }

  return resumen
}

/**
 * Pendientes ("no se pudo revisar") dejados sin red. Van despues de las
 * respuestas (el servidor descarta el pendiente de lo que ya tiene respuesta)
 * y antes del cierre (con pendientes el servidor no cierra el checklist).
 */
export async function syncPendientes(ctx, onItemDone) {
  const pending = await getPendingPendientes()
  const resumen = resumenVacio(pending.length)

  for (const row of pending) {
    const workOrderId = ctx.checklistOT.get(row.id)
    let lista = []
    try {
      lista = JSON.parse(row.local_pendientes ?? '[]')
    } catch {
      lista = []
    }
    const resultado = await intentar(
      ctx,
      {
        type: 'checklist_pending',
        key: row.id,
        workOrderId,
        log: { entityType: 'checklist', entityId: row.id, action: 'pending' },
      },
      {
        logOk: false,
        bloqueado: ctx.sinCantidad.has(row.id) || ctx.sinRespuestas.has(row.id),
        alNoSubir: () => {
          ctx.sinPendientes.add(row.id)
          ctx.sinSubir.add(workOrderId)
        },
      },
      async () => {
        try {
          await client.post(`/api/checklists/responses/${row.id}/pending/`, {
            pendientes: lista.map((p) => ({
              field: p.field ?? null,
              group: p.group ?? '',
              repetition: p.repetition ?? 0,
              reason: p.reason,
              marked_at: p.marked_at ?? null,
            })),
          })
        } catch (error) {
          // La OT ya salio de en curso: no hay nada que reintentar.
          if (!isChecklistCompleted(error)) throw error
        }
        await markPendientesSynced(row.id)
      }
    )
    contar(resumen, resultado)
    onItemDone?.()
  }
  return resumen
}

/**
 * Checklists finalizados sin red. Van despues de las respuestas (el servidor
 * rechaza cerrar uno con obligatorios sin responder) y antes del estado de la
 * OT (pasar a revision exige todos los checklists cerrados).
 */
export async function syncChecklistCompletions(ctx, onItemDone) {
  const pending = await getPendingChecklistCompletions()
  const resumen = resumenVacio(pending.length)

  for (const row of pending) {
    const workOrderId = ctx.checklistOT.get(row.id)
    const resultado = await intentar(
      ctx,
      {
        type: 'checklist_completion',
        key: row.id,
        workOrderId,
        log: { entityType: 'checklist', entityId: row.id, action: 'complete' },
      },
      {
        bloqueado:
          ctx.sinCantidad.has(row.id) || ctx.sinRespuestas.has(row.id) || ctx.sinPendientes.has(row.id),
        alNoSubir: () => ctx.sinSubir.add(workOrderId),
      },
      async () => {
        try {
          await client.post(`/api/checklists/responses/${row.id}/complete/`, {
            completed_at: row.local_completed_at ?? null,
          })
        } catch (error) {
          // Si ya estaba cerrado en el servidor (se cerro desde otra sesion),
          // el cierre en cola ya no tiene nada que hacer.
          if (!isChecklistCompleted(error)) throw error
        }
        await markChecklistCompletionSynced(row.id)
      }
    )
    contar(resumen, resultado)
    onItemDone?.()
  }

  return resumen
}

/**
 * Hallazgos creados, corregidos o quitados sin red. Van antes que las fotos
 * (una foto referencia su hallazgo) y antes del estado de la OT (enviada a
 * revision ya no se aceptan cambios). El alta manda el id del telefono: si la
 * respuesta se perdio, reenviarla devuelve el mismo hallazgo.
 */
export async function syncFindings(ctx, onItemDone) {
  const pending = await getPendingFindings()
  const resumen = resumenVacio(pending.length)

  for (const row of pending) {
    const f = JSON.parse(row.data_json)
    const resultado = await intentar(
      ctx,
      {
        type: 'finding',
        key: row.id,
        workOrderId: row.work_order_id,
        log: { entityType: 'finding', entityId: row.id, action: row.pending_action },
      },
      {
        alNoSubir: () => {
          ctx.sinHallazgo.add(row.id)
          ctx.sinSubir.add(row.work_order_id)
        },
      },
      async () => {
        if (row.pending_action === 'delete') {
          try {
            await client.delete(`/api/findings/${row.id}/`)
          } catch (error) {
            // Ya no estaba: lo que se queria, que no este.
            if (error?.response?.status !== 404) throw error
          }
          await markFindingSynced(row.id, null)
          return
        }
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
    )
    contar(resumen, resultado)
    onItemDone?.()
  }

  return resumen
}

export async function syncPhotos(ctx, onItemDone) {
  const pending = await getUnsyncedPhotos()
  const resumen = resumenVacio(pending.length)

  for (const row of pending) {
    const resultado = await intentar(
      ctx,
      {
        type: 'photo',
        key: row.offline_uuid,
        workOrderId: row.work_order_id,
        log: { entityType: 'photo', entityId: row.offline_uuid, action: 'upload' },
      },
      {
        // Foto de un hallazgo que aun no subio: el servidor no lo conoce.
        bloqueado: !!row.finding_id && ctx.sinHallazgo.has(row.finding_id),
        alNoSubir: () => ctx.sinSubir.add(row.work_order_id),
      },
      async () => {
        // La imagen se lee de a una: la lista de pendientes no la trae (con 95
        // fotos en cola eran ~100 MB en memoria).
        const archivo = await getPhotoFile(row.offline_uuid)
        if (!archivo?.startsWith('data:')) {
          // La camara nativa guarda base64 como data URL, igual que el flujo web.
          // Cualquier otra cosa es una fila corrupta y no se puede subir.
          throw new Error(`Ruta de foto no soportada: ${archivo ? archivo.slice(0, 20) : 'vacia'}`)
        }

        const file = await dataUrlToFile(archivo, `ot-${row.work_order_id}`)
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
        if (row.stage) form.append('stage', row.stage)
        // Con el identificador del telefono un reintento no duplica la foto, y el
        // campo foto del checklist ('sin-conexion:<uuid>') la encuentra despues.
        // Sin crypto.randomUUID newId() da 'local-...', que el servidor
        // rechazaria junto con la foto: ese no se manda.
        if (UUID.test(row.offline_uuid ?? '')) form.append('offline_uuid', row.offline_uuid)

        const { data } = await client.post('/api/evidence/photos/', form, {
          headers: { 'Content-Type': undefined },
        })

        await markPhotoSynced(row.offline_uuid, data.id)
      }
    )
    contar(resumen, resultado)
    onItemDone?.()
  }

  return resumen
}

export async function syncSignatures(ctx, onItemDone) {
  const pending = await getUnsyncedSignatures()
  const resumen = resumenVacio(pending.length)

  for (const row of pending) {
    const resultado = await intentar(
      ctx,
      {
        type: 'signature',
        key: row.id,
        workOrderId: row.work_order_id,
        log: { entityType: 'signature', entityId: row.id, action: 'upload' },
      },
      { alNoSubir: () => ctx.sinSubir.add(row.work_order_id) },
      async () => {
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
      }
    )
    contar(resumen, resultado)
    onItemDone?.()
  }

  return resumen
}

/**
 * El servidor rechazo el cambio de estado (ej. aprobar sin firma guardada): la
 * OT deja de mostrarse en el estado que el servidor no acepto. Se consulta el
 * estado real; si no se puede, se vuelve al de origen guardado. El motivo queda
 * en el aviso de "requiere atencion" (intentar() anota el fallo al relanzar).
 */
async function volverAlEstadoDelServidor(row) {
  let estado = null
  try {
    const { data } = await client.get(`/api/work-orders/${row.id}/`)
    estado = data?.status ?? null
  } catch {
    estado = null
  }
  // Si no hay origen guardado (cola anterior a la v9), aprobar vuelve a revision.
  if (!estado && !row.local_status_from && row.status === 'COMPLETED') estado = 'IN_REVIEW'
  await revertRejectedStatusChange(row.id, estado)
}

export async function syncWorkOrderStatuses(ctx, onItemDone) {
  const pending = await getWorkOrdersWithLocalStatusChange()
  const resumen = resumenVacio(pending.length)

  for (const row of pending) {
    const resultado = await intentar(
      ctx,
      {
        type: 'work_order',
        key: row.id,
        workOrderId: row.id,
        log: { entityType: 'work_order', entityId: row.id, action: 'transition' },
      },
      // El servidor valida que todo lo de la OT este arriba antes de moverla.
      { bloqueado: ctx.sinSubir.has(row.id) },
      async () => {
        try {
          await client.post(`/api/work-orders/${row.id}/transition/`, {
            new_status: row.status,
            comment: row.local_status_comment ?? 'Cambio realizado sin conexion',
            // Hora del telefono al hacerlo sin red: el servidor la acepta con
            // tolerancia (device_time) para el acta; sin ella usa la suya.
            ...(row.local_status_at ? { client_timestamp: row.local_status_at } : {}),
          })
        } catch (error) {
          if (esRechazoDeTransicion(error)) await volverAlEstadoDelServidor(row)
          throw error
        }
        await markWorkOrderStatusSynced(row.id)
      }
    )
    contar(resumen, resultado)
    onItemDone?.()
  }

  return resumen
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

  // El orden es deliberado: cantidad de tomas, respuestas, pendientes, cierre de cada
  // checklist, hallazgos (antes que las fotos que los referencian), evidencia
  // y al final el estado de la OT, que valida todo lo anterior.
  const ctx = await nuevoContexto()
  const counts = await syncBlockCounts(ctx, tick)
  const fields = await syncFieldResponses(ctx, tick)
  const pendientes = await syncPendientes(ctx, tick)
  const checklists = await syncChecklistCompletions(ctx, tick)
  const findings = await syncFindings(ctx, tick)
  const photos = await syncPhotos(ctx, tick)
  const signatures = await syncSignatures(ctx, tick)
  const workOrders = await syncWorkOrderStatuses(ctx, tick)

  const result = { counts, fields, pendientes, checklists, findings, photos, signatures, workOrders }
  const fases = Object.values(result)
  const failed = fases.reduce((acc, f) => acc + f.failed, 0)
  const synced = fases.reduce((acc, f) => acc + f.ok, 0)

  onProgress?.(await countPendingSync())

  if (synced || failed) {
    console.info(`[sync] ${synced} elementos subidos, ${failed} con error`, result)
  }
  return result
}
