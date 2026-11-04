import assert from 'node:assert/strict'
import { test } from 'node:test'

import { asignadoA, avisoHistorica, esHistorica, etiquetaOrigen, textoFotosPendientes } from './otHistorica.js'

const historica = { origin: 'FRACTTAL', fracttal_folio: '4521', external_executor: 'Juan Pérez', fracttal_photos_pending: 3 }
const normal = { origin: '', assigned_to: { full_name: 'Ana Gómez' } }

test('solo es histórica si trae origen', () => {
  assert.equal(esHistorica(historica), true)
  assert.equal(esHistorica(normal), false)
  assert.equal(esHistorica(null), false)
})

test('el aviso lleva el folio y solo sale en las históricas', () => {
  assert.equal(avisoHistorica(historica), 'OT histórica importada de Fracttal · folio N° 4521. Solo consulta.')
  assert.equal(avisoHistorica({ origin: 'FRACTTAL' }), 'OT histórica importada de Fracttal. Solo consulta.')
  assert.equal(avisoHistorica(normal), null)
})

test('asignado a muestra al ejecutor de Fracttal en las históricas', () => {
  assert.deepEqual(asignadoA(historica), { etiqueta: 'Ejecutó (Fracttal)', valor: 'Juan Pérez' })
  assert.deepEqual(asignadoA({ origin: 'FRACTTAL' }), { etiqueta: 'Ejecutó (Fracttal)', valor: '—' })
  assert.deepEqual(asignadoA(normal), { etiqueta: 'Asignado a', valor: 'Ana Gómez' })
  assert.deepEqual(asignadoA({ origin: '' }), { etiqueta: 'Asignado a', valor: '—' })
})

test('fotos pendientes en singular y plural, y nada si no hay', () => {
  assert.equal(textoFotosPendientes(historica), '3 fotos quedaron en Fracttal y aún no se han traído')
  assert.equal(textoFotosPendientes({ ...historica, fracttal_photos_pending: 1 }), '1 foto quedó en Fracttal y aún no se ha traído')
  assert.equal(textoFotosPendientes({ ...historica, fracttal_photos_pending: 0 }), null)
  assert.equal(textoFotosPendientes(normal), null)
})

test('etiqueta de la lista', () => {
  assert.equal(etiquetaOrigen(historica), 'Fracttal')
  assert.equal(etiquetaOrigen(normal), null)
})
