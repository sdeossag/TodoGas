/**
 * Migracion de la base offline de la v1 a la v2 (fase 3 del modelo de tareas).
 *
 * Lo que se prueba es lo que no puede fallar en un telefono: que una base v1
 * con respuestas, fotos, firmas y cambios de estado sin sincronizar pase a la
 * v2 sin perder nada, y que una migracion cortada a la mitad se pueda terminar.
 *
 *   npm test
 */

import assert from 'node:assert/strict'
import { test } from 'node:test'
import initSqlJs from 'sql.js'

import { LATEST_VERSION, currentVersion, migrate } from './migrations.js'
import { CREATE_TABLES_V1 } from './schema.js'

const SQL = await initSqlJs()

/** Mismo contrato que webDriver/nativeDriver: execute, run, query. */
function driverFor(db) {
  return {
    async execute(statement) {
      db.run(statement)
    },
    async run(statement, values = []) {
      db.run(statement, values)
    },
    async query(statement, values = []) {
      const stmt = db.prepare(statement)
      try {
        if (values.length) stmt.bind(values)
        const rows = []
        while (stmt.step()) rows.push(stmt.getAsObject())
        return rows
      } finally {
        stmt.free()
      }
    },
  }
}

/** Una base como la de un telefono con la app v1 y trabajo sin subir. */
async function baseV1ConPendientes() {
  const db = new SQL.Database()
  const d = driverFor(db)
  for (const s of CREATE_TABLES_V1) await d.execute(s)
  // La v1 nunca escribio user_version: queda en 0.
  await d.run(
    `INSERT INTO offline_work_orders (id, wo_number, title, status, assigned_to_id,
       raw_json, local_status_changed, local_status_comment)
     VALUES ('wo-1', 7, 'Alarma', 'IN_REVIEW', 'tec-1', '{"id":"wo-1"}', 1, 'sin red')`
  )
  await d.run(
    `INSERT INTO offline_checklist_responses (id, work_order_id, version_id, version_fields_json)
     VALUES ('cr-1', 'wo-1', 'v-1', '[{"id":"f-1"}]')`
  )
  await d.run(
    `INSERT INTO offline_field_responses (id, response_id, field_id, value, synced)
     VALUES ('fr-1', 'cr-1', 'f-1', '55', 0)`
  )
  await d.run(
    `INSERT INTO offline_photos (id, work_order_id, file_path, synced, offline_uuid)
     VALUES ('ph-1', 'wo-1', 'data:image/jpeg;base64,AAAA', 0, 'ph-1')`
  )
  await d.run(
    `INSERT INTO offline_signatures (id, work_order_id, signature_type, image_base64, synced)
     VALUES ('sg-1', 'wo-1', 'TECHNICIAN', 'data:image/png;base64,BBBB', 0)`
  )
  return { db, d }
}

async function pendientes(d) {
  const [row] = await d.query(`SELECT
     (SELECT COUNT(*) FROM offline_field_responses WHERE synced = 0) AS campos,
     (SELECT COUNT(*) FROM offline_photos WHERE synced = 0) AS fotos,
     (SELECT COUNT(*) FROM offline_signatures WHERE synced = 0) AS firmas,
     (SELECT COUNT(*) FROM offline_work_orders WHERE local_status_changed = 1) AS estados`)
  return row
}

async function columnas(d, tabla) {
  return (await d.query(`PRAGMA table_info(${tabla})`)).map((r) => r.name)
}

test('una base nueva queda en la ultima version', async () => {
  const d = driverFor(new SQL.Database())
  assert.equal(await currentVersion(d), 0)

  assert.equal(await migrate(d), LATEST_VERSION)

  const [{ user_version }] = await d.query('PRAGMA user_version')
  assert.equal(user_version, LATEST_VERSION)
  assert.ok((await columnas(d, 'offline_checklist_responses')).includes('task_id'))
})

test('una base v1 sin user_version se reconoce como v1', async () => {
  const { d } = await baseV1ConPendientes()
  assert.equal(await currentVersion(d), 1)
})

test('la v1 pasa a la v2 sin perder nada pendiente de subir', async () => {
  const { d } = await baseV1ConPendientes()
  const antes = await pendientes(d)

  await migrate(d)

  assert.deepEqual(await pendientes(d), antes)
  assert.deepEqual(antes, { campos: 1, fotos: 1, firmas: 1, estados: 1 })
  const [wo] = await d.query("SELECT * FROM offline_work_orders WHERE id = 'wo-1'")
  assert.equal(wo.local_status_comment, 'sin red')
  assert.equal(wo.raw_json, '{"id":"wo-1"}')
  const [cr] = await d.query("SELECT * FROM offline_checklist_responses WHERE id = 'cr-1'")
  assert.equal(cr.version_fields_json, '[{"id":"f-1"}]')
  assert.equal(cr.task_id, null)
  assert.equal(cr.completion_pending, 0)
  const [ph] = await d.query("SELECT * FROM offline_photos WHERE id = 'ph-1'")
  assert.equal(ph.file_path, 'data:image/jpeg;base64,AAAA')
  assert.equal(ph.task_id, null)
})

test('migrar dos veces no hace nada la segunda', async () => {
  const { d } = await baseV1ConPendientes()
  await migrate(d)
  const antes = await columnas(d, 'offline_work_orders')

  assert.equal(await migrate(d), LATEST_VERSION)

  assert.deepEqual(await columnas(d, 'offline_work_orders'), antes)
})

test('una migracion cortada a la mitad se termina al volver a abrir', async () => {
  const { d } = await baseV1ConPendientes()
  // La app se cerro despues de agregar una columna y antes de subir la version.
  await d.execute('ALTER TABLE offline_photos ADD COLUMN task_id TEXT')
  await d.execute('PRAGMA user_version = 1')

  assert.equal(await migrate(d), LATEST_VERSION)

  assert.ok((await columnas(d, 'offline_checklist_responses')).includes('response_json'))
  assert.deepEqual(await pendientes(d), { campos: 1, fotos: 1, firmas: 1, estados: 1 })
})
