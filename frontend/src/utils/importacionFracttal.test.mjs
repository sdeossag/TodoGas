import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  filtrarFilas, contarFilas, puedeImportar, textoBotonImportar, textoResultado, textoProtocolos,
  hayArchivos, errorDeArchivo, textoEquipos,
} from './importacionFracttal.js'

const rows = [
  { row: 2, errors: [], warnings: [] },
  { row: 3, errors: ['Falta nombre'], warnings: [] },
  { row: 4, errors: [], warnings: ['Sin serie'] },
]

test('filtra filas por errores y avisos', () => {
  assert.equal(filtrarFilas(rows, 'todas').length, 3)
  assert.deepEqual(filtrarFilas(rows, 'errores').map((r) => r.row), [3])
  assert.deepEqual(filtrarFilas(rows, 'avisos').map((r) => r.row), [4])
  assert.deepEqual(filtrarFilas(undefined, 'errores'), [])
})

test('cuenta las filas por filtro', () => {
  assert.deepEqual(contarFilas(rows), { todas: 3, errores: 1, avisos: 1 })
})

test('no se puede importar con errores ni sin nada que hacer', () => {
  const base = { hospitals: { create: [] }, locations: { create: 1, update: 0 }, assets: { create: 2, update: 0 } }
  assert.equal(puedeImportar({ ...base, errors_count: 0 }), true)
  assert.equal(puedeImportar({ ...base, errors_count: 1 }), false)
  assert.equal(puedeImportar({ ...base, locations: { create: 0, update: 0 }, assets: { create: 0, update: 0 }, errors_count: 0 }), false)
  assert.equal(puedeImportar(null), false)
})

test('textos con singular y plural', () => {
  assert.equal(textoEquipos(1), '1 equipo')
  const r = { locations: { create: 1, update: 2 }, assets: { create: 3, update: 0 } }
  assert.equal(textoBotonImportar(r), 'Importar 3 equipos y 3 ubicaciones')
  assert.deepEqual(
    textoResultado({ hospitals: { create: ['A'] }, locations: { create: 1, update: 2 }, assets: { create: 3, update: 1 } }),
    ['1 hospital nuevo', '1 ubicación creada', '2 ubicaciones actualizadas', '3 equipos creados', '1 equipo actualizado'],
  )
})

test('protocolos por crear en el texto del resultado', () => {
  assert.equal(textoProtocolos(1), '1 protocolo')
  assert.equal(textoProtocolos(3), '3 protocolos')
  const base = { locations: {}, assets: {} }
  assert.deepEqual(textoResultado({ ...base, plans: { create: ['A', 'B'] } }), ['2 protocolos creados vacíos'])
  assert.deepEqual(
    textoResultado({ ...base, plans: { create: ['A'] }, applied_counts: { plans_created: 1 } }),
    ['1 protocolo creado vacío'],
  )
  assert.deepEqual(textoResultado({ ...base, plans: { create: [] } }), [])
})

test('valida los archivos antes de enviarlos', () => {
  assert.equal(hayArchivos({}), false)
  assert.equal(hayArchivos({ equipos: { name: 'a.xlsx' } }), true)
  assert.equal(errorDeArchivo({ name: 'a.xlsx', size: 100 }), null)
  assert.ok(errorDeArchivo({ name: 'a.csv', size: 100 }))
  assert.ok(errorDeArchivo({ name: 'a.xlsx', size: 11 * 1024 * 1024 }))
})
