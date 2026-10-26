import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  agruparPorArea, cuantosExtra, esGestor, permisosDe, puede, puedeAlguno, veOrdenes,
} from './permisos.js'

const tec = (extra = {}) => ({ role: 'TEC', ...extra })

test('un técnico sin permisos no puede nada de gestión', () => {
  const u = tec({ permisos: [] })
  assert.equal(puede(u, 'ot.revisar'), false)
  assert.equal(esGestor(u), false)
  assert.equal(veOrdenes(u), false)
})

test('un técnico con "revisar" ve las órdenes y puede aprobar, pero no cancelar', () => {
  const u = tec({ permisos: ['ot.revisar'], permisos_extra: ['ot.revisar'] })
  assert.equal(puede(u, 'ot.revisar'), true)
  assert.equal(puede(u, 'ot.cancelar'), false)
  assert.equal(esGestor(u), true)
  assert.equal(veOrdenes(u), true)
  assert.equal(cuantosExtra(u), 1)
})

test('con solo "inventario" entra a gestión pero no ve la lista de órdenes', () => {
  const u = tec({ permisos: ['inventario.movimientos'] })
  assert.equal(esGestor(u), true)
  assert.equal(veOrdenes(u), false)
})

test('un perfil guardado antes de esta versión usa los permisos del rol', () => {
  assert.equal(puede({ role: 'SUP' }, 'ot.revisar'), true)
  assert.equal(puede({ role: 'SUP' }, 'ot.cancelar'), false)
  assert.equal(puede({ role: 'ADMIN' }, 'ot.cancelar'), true)
  assert.deepEqual(permisosDe({ role: 'TEC' }), [])
  assert.equal(esGestor({ role: 'SUP' }), true)
})

test('la cuenta de un hospital nunca entra a gestión', () => {
  assert.equal(esGestor({ role: 'CLI', permisos: ['ot.revisar'] }), false)
  assert.equal(veOrdenes({ role: 'CLI', permisos: ['ot.revisar'] }), false)
})

test('puedeAlguno acepta cualquiera de la lista', () => {
  const u = tec({ permisos: ['tareas.planificar'] })
  assert.equal(puedeAlguno(u, 'ot.crear_desde_pendientes', 'tareas.planificar'), true)
  assert.equal(puedeAlguno(u, 'ot.cancelar'), false)
})

test('agrupa el catálogo por área en orden', () => {
  const g = agruparPorArea([
    { codigo: 'a', area: 'X' }, { codigo: 'b', area: 'Y' }, { codigo: 'c', area: 'X' },
  ])
  assert.deepEqual(g.map((x) => [x.area, x.permisos.length]), [['X', 2], ['Y', 1]])
})
