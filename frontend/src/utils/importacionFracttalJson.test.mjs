import test from 'node:test'
import assert from 'node:assert/strict'
import { errorDeArchivoJson, puedeImportarJson, textoResultadoJson } from './importacionFracttalJson.js'

test('solo acepta .json y hasta 100 MB', () => {
  assert.equal(errorDeArchivoJson(null), '')
  assert.equal(errorDeArchivoJson({ name: 'a.JSON', size: 10 }), '')
  assert.match(errorDeArchivoJson({ name: 'a.xlsx', size: 10 }), /JSON/)
  assert.match(errorDeArchivoJson({ name: 'a.json', size: 101 * 1024 * 1024 }), /100 MB/)
})

test('no se puede importar con errores ni sin nada que hacer', () => {
  assert.equal(puedeImportarJson(null), false)
  assert.equal(puedeImportarJson({ errors_count: 1, assets: { create: 5 } }), false)
  assert.equal(puedeImportarJson({ errors_count: 0 }), false)
  assert.equal(puedeImportarJson({ errors_count: 0, work_orders: { create: 2 } }), true)
})

test('texto de lo que se guarda', () => {
  const t = textoResultadoJson({
    hospitals: { create: ['A'] }, locations: { create: 2, update: 1 }, assets: { create: 0, update: 3 },
    plans: { create: 1, update: 0 }, work_orders: { create: 1 },
  })
  assert.deepEqual(t, [
    '1 hospital nuevo', 'ubicaciones: 2 nuevas, 1 se actualizan', 'equipos: 0 nuevos, 3 se actualizan',
    'protocolos: 1 nuevos, 0 existentes', '1 OT histórica',
  ])
})
