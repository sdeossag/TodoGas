/**
 * Migraciones de la base offline, por PRAGMA user_version.
 *
 * Hasta la v1 las tablas se creaban con "IF NOT EXISTS" y nada llevaba la
 * cuenta de la version: cambiar el esquema en un telefono con datos sin
 * sincronizar no tenia camino. Ahora cada migracion sube user_version y solo
 * corre si la base esta por debajo.
 *
 * Reglas, porque en el telefono puede haber respuestas, fotos y firmas que
 * todavia no llegaron al servidor:
 *   - nunca se borra ni se recrea una tabla con datos: solo se agregan
 *     columnas, indices o tablas nuevas;
 *   - cada paso es reanudable: si la app se cierra a mitad de una migracion,
 *     al volver a abrirla termina sin fallar por una columna que ya existe.
 *
 * El modulo no importa nada de Capacitor ni de Vite: la prueba lo corre en
 * Node sobre sql.js (migrations.test.mjs).
 */

import { CREATE_TABLES_V1 } from './schema.js'

async function columns(driver, table) {
  const rows = await driver.query(`PRAGMA table_info(${table})`)
  return new Set(rows.map((r) => r.name))
}

async function addColumn(driver, table, column, definition) {
  if ((await columns(driver, table)).has(column)) return
  await driver.execute(`ALTER TABLE ${table} ADD COLUMN ${column} ${definition}`)
}

export const MIGRATIONS = [
  {
    version: 1,
    async up(driver) {
      for (const statement of CREATE_TABLES_V1) await driver.execute(statement)
    },
  },
  {
    // Fase 3 del modelo de tareas: una OT trae varias tareas, cada una con su
    // checklist, y las fotos se atribuyen a un activo.
    version: 2,
    async up(driver) {
      // El detalle completo de la OT con sus tareas, tal como lo da el
      // paquete offline del servidor; raw_json sigue siendo la fila de la lista.
      await addColumn(driver, 'offline_work_orders', 'detail_json', 'TEXT')
      await addColumn(driver, 'offline_work_orders', 'location_name', 'TEXT')
      await addColumn(driver, 'offline_work_orders', 'assets_count', 'INTEGER')

      // Un checklist por tarea. response_json guarda la respuesta completa
      // (campos y respuestas) para poder abrirla sin red. Finalizar sin red
      // queda en cola: completion_pending lo marca para el motor de sincronizacion.
      await addColumn(driver, 'offline_checklist_responses', 'task_id', 'TEXT')
      await addColumn(driver, 'offline_checklist_responses', 'response_json', 'TEXT')
      await addColumn(driver, 'offline_checklist_responses', 'local_completed_at', 'TEXT')
      await addColumn(driver, 'offline_checklist_responses', 'completion_pending', 'INTEGER DEFAULT 0')

      await addColumn(driver, 'offline_photos', 'task_id', 'TEXT')

      await driver.execute(
        `CREATE INDEX IF NOT EXISTS idx_checklist_responses_task
           ON offline_checklist_responses (task_id)`
      )
      await driver.execute(
        `CREATE INDEX IF NOT EXISTS idx_checklist_responses_pending
           ON offline_checklist_responses (completion_pending)`
      )
    },
  },
]

export const LATEST_VERSION = MIGRATIONS[MIGRATIONS.length - 1].version

/**
 * Version en la que esta la base. Las creadas antes de que existieran las
 * migraciones tienen user_version 0 pero ya tienen las tablas de la v1.
 */
export async function currentVersion(driver) {
  const [row] = await driver.query('PRAGMA user_version')
  const version = Number(row?.user_version ?? 0)
  if (version > 0) return version
  const legacy = await driver.query(
    "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'offline_work_orders'"
  )
  return legacy.length ? 1 : 0
}

/** Lleva la base a la ultima version. Devuelve la version final. */
export async function migrate(driver) {
  let version = await currentVersion(driver)
  for (const migration of MIGRATIONS) {
    if (migration.version <= version) continue
    await migration.up(driver)
    await driver.execute(`PRAGMA user_version = ${migration.version}`)
    version = migration.version
  }
  return version
}
