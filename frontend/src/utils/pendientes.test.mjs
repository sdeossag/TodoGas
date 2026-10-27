import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  conPendiente,
  pendienteDeBloque,
  pendienteDeCampo,
  pendientesVigentes,
  resumenPendientes,
  sinPendiente,
  sinPendientesAlResponder,
  sinPendientesDeTomasQueSobran,
  textoPendiente,
} from './pendientes.js'

const campos = [
  { id: 'f-loc', label: 'Localización', group: '' },
  { id: 'f-pres', label: 'Presión', group: 'Cubículo' },
]
const respuesta = (extra = {}) => ({
  repeatable_groups: ['Cubículo'],
  version_fields: campos,
  field_responses: [],
  pendientes: [],
  ...extra,
})

test('el pendiente exige motivo', () => {
  assert.throws(() => conPendiente([], { group: 'Cubículo', repetition: 7, reason: '   ' }))
  assert.throws(() => conPendiente([], { group: 'Cubículo', repetition: 7 }))
})

test('un bloque pendiente se agrega, se lee y se reemplaza sin duplicarse', () => {
  let l = conPendiente([], { group: 'Cubículo', repetition: 7, reason: ' aislado por aerosoles ' })
  assert.equal(l.length, 1)
  assert.equal(l[0].reason, 'aislado por aerosoles')
  assert.ok(pendienteDeBloque(l, 'Cubículo', 7))
  assert.equal(pendienteDeBloque(l, 'Cubículo', 6), null)
  const marcado = l[0].marked_at
  l = conPendiente(l, { group: 'Cubículo', repetition: 7, reason: 'sin llave' })
  assert.equal(l.length, 1)
  assert.equal(l[0].reason, 'sin llave')
  assert.equal(l[0].marked_at, marcado, 'conserva la hora en que se marcó')
})

test('un campo pendiente y un bloque pendiente son cosas distintas', () => {
  let l = conPendiente([], { field: 'f-pres', group: 'Cubículo', repetition: 2, reason: 'tapado' })
  l = conPendiente(l, { group: 'Cubículo', repetition: 2, reason: 'aislado' })
  assert.equal(l.length, 2)
  assert.ok(pendienteDeCampo(l, 'f-pres', 2))
  assert.equal(pendienteDeCampo(l, 'f-pres', 3), null)
  assert.equal(l.find((p) => p.field).group, '', 'el de campo no lleva grupo')
})

test('quitar un pendiente deja los demás', () => {
  let l = conPendiente([], { group: 'Cubículo', repetition: 7, reason: 'a' })
  l = conPendiente(l, { group: 'Cubículo', repetition: 8, reason: 'b' })
  l = sinPendiente(l, { group: 'Cubículo', repetition: 7 })
  assert.deepEqual(l.map((p) => p.repetition), [8])
})

test('responder un campo quita su pendiente y el del bloque de esa toma', () => {
  const r = respuesta()
  let l = conPendiente([], { group: 'Cubículo', repetition: 7, reason: 'a' })
  l = conPendiente(l, { field: 'f-loc', repetition: 0, reason: 'sin acceso' })
  l = conPendiente(l, { group: 'Cubículo', repetition: 8, reason: 'b' })
  l = sinPendientesAlResponder(l, r, campos[1], 7)
  assert.equal(l.length, 2)
  assert.ok(pendienteDeBloque(l, 'Cubículo', 8))
  l = sinPendientesAlResponder(l, r, campos[0], 0)
  assert.deepEqual(l.map((p) => p.repetition), [8])
})

test('un campo que no se repite no quita bloques', () => {
  const r = respuesta()
  const l = conPendiente([], { group: 'Cubículo', repetition: 0, reason: 'a' })
  assert.equal(sinPendientesAlResponder(l, r, campos[0], 0).length, 1)
})

test('bajar la cantidad de tomas descarta los pendientes de las que sobran', () => {
  let l = conPendiente([], { group: 'Cubículo', repetition: 2, reason: 'a' })
  l = conPendiente(l, { group: 'Cubículo', repetition: 5, reason: 'b' })
  assert.deepEqual(sinPendientesDeTomasQueSobran(l, 'Cubículo', 3).map((p) => p.repetition), [2])
})

test('el texto es el mismo que el del servidor', () => {
  const b = { field: null, group: 'Cubículo', repetition: 7, reason: 'aislado por aerosoles' }
  assert.equal(textoPendiente(b, campos), 'Cubículo 7: pendiente — aislado por aerosoles')
  assert.equal(
    textoPendiente({ field: 'f-pres', repetition: 3, reason: 'tapado' }, campos),
    'Cubículo 3: Presión: pendiente — tapado'
  )
  assert.equal(
    textoPendiente({ field: 'f-loc', repetition: 0, reason: 'sin acceso' }, campos),
    'Localización: pendiente — sin acceso'
  )
})

test('un pendiente de un campo que ya tiene respuesta no cuenta', () => {
  const r = respuesta({
    pendientes: [
      { field: 'f-pres', group: '', repetition: 2, reason: 'x' },
      { field: null, group: 'Cubículo', repetition: 7, reason: 'aislado' },
    ],
    field_responses: [{ field: 'f-pres', repetition: 2, value: '50' }],
  })
  assert.equal(pendientesVigentes(r).length, 1)
  const resumen = resumenPendientes(r)
  assert.equal(resumen.pending_count, 1)
  assert.deepEqual(resumen.pending, ['Cubículo 7: pendiente — aislado'])
})

test('los pendientes de la OT se nombran, con el activo si hay varias tareas', async () => {
  const { pendientesDeLaOt } = await import('./pendientes.js')
  const una = [{ status: 'IN_PROGRESS', asset: { name: 'Alarma' },
    checklist: { pending: ['Cubículo 7: pendiente — aislado'] } }]
  assert.deepEqual(pendientesDeLaOt(una), ['Cubículo 7: pendiente — aislado'])
  const varias = [
    ...una,
    { status: 'IN_PROGRESS', asset: { name: 'Manifold' }, checklist: { pending: ['Fuga: pendiente — sin llave'] } },
    { status: 'CANCELLED', asset: { name: 'Otro' }, checklist: { pending: ['x: pendiente — y'] } },
  ]
  assert.deepEqual(pendientesDeLaOt(varias), [
    'Alarma · Cubículo 7: pendiente — aislado',
    'Manifold · Fuga: pendiente — sin llave',
  ])
  assert.deepEqual(pendientesDeLaOt([{ status: 'PENDING', asset: {}, checklist: null }]), [])
})
