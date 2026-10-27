import assert from 'node:assert/strict'
import { test } from 'node:test'

import { CATEGORIAS, categoriaDe, contarPorCategoria, filtrarPorCategoria } from './tiposDeTarea.js'

const tareas = [
  { id: 'a', task_type_counts_as: 'PREVENTIVE' },
  { id: 'b', task_type_counts_as: 'CORRECTIVE' },
  { id: 'c', task_type_counts_as: 'OTHER' },
  { id: 'd', task_type_counts_as: 'PREVENTIVE' },
  { id: 'e' },
  { id: 'f', task_type_counts_as: 'RARO' },
]

test('las categorias son preventivo, correctivo y otro, con etiqueta en español', () => {
  assert.deepEqual(
    CATEGORIAS.map((c) => [c.clave, c.etiqueta]),
    [['PREVENTIVE', 'Preventivo'], ['CORRECTIVE', 'Correctivo'], ['OTHER', 'Otro']],
  )
  for (const c of CATEGORIAS) assert.ok(c.cls.length > 0)
})

test('lo que no es una categoria conocida cuenta como otro', () => {
  assert.equal(categoriaDe({ task_type_counts_as: 'CORRECTIVE' }), 'CORRECTIVE')
  assert.equal(categoriaDe({}), 'OTHER')
  assert.equal(categoriaDe({ task_type_counts_as: 'RARO' }), 'OTHER')
  assert.equal(categoriaDe(undefined), 'OTHER')
})

test('ALL devuelve todas las tareas', () => {
  assert.equal(filtrarPorCategoria(tareas, 'ALL').length, 6)
})

test('filtra por categoria', () => {
  assert.deepEqual(filtrarPorCategoria(tareas, 'PREVENTIVE').map((t) => t.id), ['a', 'd'])
  assert.deepEqual(filtrarPorCategoria(tareas, 'CORRECTIVE').map((t) => t.id), ['b'])
  assert.deepEqual(filtrarPorCategoria(tareas, 'OTHER').map((t) => t.id), ['c', 'e', 'f'])
})

test('cuenta por categoria con el total en ALL', () => {
  assert.deepEqual(contarPorCategoria(tareas), { ALL: 6, PREVENTIVE: 2, CORRECTIVE: 1, OTHER: 3 })
  assert.deepEqual(contarPorCategoria([]), { ALL: 0, PREVENTIVE: 0, CORRECTIVE: 0, OTHER: 0 })
  assert.deepEqual(contarPorCategoria(undefined), { ALL: 0, PREVENTIVE: 0, CORRECTIVE: 0, OTHER: 0 })
})
