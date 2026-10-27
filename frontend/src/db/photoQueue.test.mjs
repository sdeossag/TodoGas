/**
 * Cola de fotos sin red con una OT de INVIMA: 95 fotos.
 *
 * Lo que no puede fallar en el telefono es la memoria: la lista de pendientes
 * y el conteo no deben traer las imagenes, y la imagen se lee de a una.
 *
 *   npm test
 */

import assert from 'node:assert/strict'
import { test } from 'node:test'
import initSqlJs from 'sql.js'

import { CREATE_TABLES_V1 } from './schema.js'
import { migrate } from './migrations.js'
import { contarPendientes, leerArchivo, listarPendientes, marcarSubida } from './photoQueue.js'

const SQL = await initSqlJs()

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

const FOTOS = 95
// ~100 KB de base64 por foto: lo bastante grande para notar si se carga.
const IMAGEN = `data:image/jpeg;base64,${'A'.repeat(100_000)}`

async function colaConFotos(n = FOTOS) {
  const d = driverFor(new SQL.Database())
  for (const s of CREATE_TABLES_V1) await d.execute(s)
  await migrate(d)
  for (let i = 0; i < n; i += 1) {
    await d.run(
      `INSERT INTO offline_photos (id, work_order_id, file_path, taken_at, synced, offline_uuid, stage)
       VALUES (?,?,?,?,0,?,?)`,
      [`p-${i}`, i < n - 5 ? 'wo-1' : 'wo-2', IMAGEN, `2026-10-23T10:${String(i % 60).padStart(2, '0')}:00Z`, `u-${i}`, i % 2 ? 'BEFORE' : 'AFTER']
    )
  }
  return d
}

test('95 fotos en cola: la lista de pendientes no trae ninguna imagen', async () => {
  const d = await colaConFotos()
  const todas = await listarPendientes(d)
  assert.equal(todas.length, FOTOS)
  assert.ok(todas.every((f) => !('file_path' in f)), 'ninguna fila debe llevar la imagen')
  // Y trae lo necesario para subirla.
  assert.deepEqual(
    Object.keys(todas[0]).sort(),
    ['caption', 'file_hash', 'finding_id', 'id', 'latitude', 'longitude', 'offline_uuid', 'stage', 'synced', 'task_id', 'taken_at', 'work_order_id'].sort()
  )
  assert.equal((await listarPendientes(d, 'wo-1')).length, FOTOS - 5)
})

test('contar las fotos de una OT no lee imagenes y da el total exacto', async () => {
  const d = await colaConFotos()
  assert.equal(await contarPendientes(d, 'wo-1'), FOTOS - 5)
  assert.equal(await contarPendientes(d, 'wo-2'), 5)
  assert.equal(await contarPendientes(d, 'wo-sin-fotos'), 0)
})

test('la imagen se lee de a una, por su identificador', async () => {
  const d = await colaConFotos()
  assert.equal(await leerArchivo(d, 'u-7'), IMAGEN)
  assert.equal(await leerArchivo(d, 'no-existe'), null)
})

test('subir las 95 una por una vacia la cola y libera las imagenes del telefono', async () => {
  const d = await colaConFotos()
  for (const foto of await listarPendientes(d)) {
    const archivo = await leerArchivo(d, foto.offline_uuid)
    assert.equal(archivo, IMAGEN)
    await marcarSubida(d, foto.offline_uuid, `srv-${foto.id}`)
  }
  assert.equal((await listarPendientes(d)).length, 0)
  assert.equal(await contarPendientes(d, 'wo-1'), 0)
  const [resto] = await d.query('SELECT COUNT(*) AS n FROM offline_photos WHERE file_path IS NOT NULL')
  assert.equal(resto.n, 0, 'ya estan en el servidor: no se guardan dos veces')
  const [subidas] = await d.query("SELECT COUNT(*) AS n FROM offline_photos WHERE synced = 1 AND id LIKE 'srv-%'")
  assert.equal(subidas.n, FOTOS)
})

test('una foto que fallo sigue en la cola con su imagen para el reintento', async () => {
  const d = await colaConFotos(3)
  await marcarSubida(d, 'u-0', 'srv-0')
  const pendientes = await listarPendientes(d)
  assert.deepEqual(pendientes.map((f) => f.offline_uuid), ['u-1', 'u-2'])
  assert.equal(await leerArchivo(d, 'u-1'), IMAGEN)
})
