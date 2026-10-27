/**
 * Cola de fotos pendientes de subir (tabla offline_photos).
 *
 * Cada foto se guarda en SQLite como data URL (base64): una foto de 1920 px son
 * ~1 MB y una OT de INVIMA puede llevar hasta 95. Por eso nada de aqui carga
 * todas las fotos a la vez: las listas traen solo los datos (sin la imagen), y
 * la imagen se lee de a una, justo antes de subirla. Antes `SELECT *` metia en
 * memoria las 95 imagenes (~100 MB en el WebView) para subirlas en fila y,
 * ademas, para contarlas al revisar los requisitos de la OT.
 *
 * Recibe el driver (execute/run/query) para poder probarse en Node con sql.js.
 */

// Todo menos file_path.
const COLUMNAS = `id, work_order_id, latitude, longitude, taken_at, caption, file_hash,
  synced, offline_uuid, task_id, finding_id, stage`

/** Fotos sin subir, sin la imagen. De una OT, o de todas; en orden de captura. */
export function listarPendientes(driver, workOrderId = null) {
  const donde = workOrderId ? 'synced = 0 AND work_order_id = ?' : 'synced = 0'
  return driver.query(
    `SELECT ${COLUMNAS} FROM offline_photos WHERE ${donde} ORDER BY taken_at, rowid`,
    workOrderId ? [workOrderId] : []
  )
}

/** Cuantas fotos de la OT siguen sin subir (sin leer ninguna imagen). */
export async function contarPendientes(driver, workOrderId) {
  const [fila] = await driver.query(
    'SELECT COUNT(*) AS n FROM offline_photos WHERE synced = 0 AND work_order_id = ?',
    [workOrderId]
  )
  return fila?.n ?? 0
}

/** La imagen (data URL) de una foto; null si no existe o ya se libero. */
export async function leerArchivo(driver, offlineUuid) {
  const [fila] = await driver.query('SELECT file_path FROM offline_photos WHERE offline_uuid = ?', [
    offlineUuid,
  ])
  return fila?.file_path ?? null
}

/**
 * Foto subida: queda marcada con el id del servidor y se suelta la imagen.
 * Ya esta en el servidor; guardarla otra vez en el telefono solo hace crecer
 * la base (95 fotos son ~100 MB) y nada la vuelve a leer.
 */
export function marcarSubida(driver, offlineUuid, serverId) {
  return driver.run(
    'UPDATE offline_photos SET synced = 1, id = ?, file_path = NULL WHERE offline_uuid = ?',
    [serverId, offlineUuid]
  )
}
