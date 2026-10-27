import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  MAX_ACTAS_REENVIO,
  agruparPorHospital,
  alternarTodas,
  esReenviable,
  excedeLimite,
  resumenGrupos,
  textoGrupo,
  textoSeleccion,
  todasMarcadas,
} from './reenvioActas.js'

const acta = (id, hospital) => ({
  id,
  work_order: hospital ? { id: `wo-${id}`, hospital } : null,
})
const H1 = { id: 'h1', name: 'Zeta', contact_email: 'z@h.co' }
const H2 = { id: 'h2', name: 'Alfa', contact_email: '' }
const reports = [acta('a', H1), acta('b', H2), acta('c', H1), acta('d', null)]

test('el límite es 50 y se excede a partir de 51', () => {
  assert.equal(MAX_ACTAS_REENVIO, 50)
  assert.equal(excedeLimite(50), false)
  assert.equal(excedeLimite(51), true)
})

test('textos de la selección en singular y plural', () => {
  assert.equal(textoSeleccion(1), '1 acta seleccionada')
  assert.equal(textoSeleccion(3), '3 actas seleccionadas')
})

test('las actas sin OT no se pueden reenviar', () => {
  assert.equal(esReenviable(reports[3]), false)
  assert.equal(esReenviable(reports[0]), true)
})

test('agrupa lo seleccionado por hospital en orden alfabético', () => {
  const g = agruparPorHospital(reports, new Set(['a', 'b', 'c', 'd']))
  assert.deepEqual(g, [
    { hospital_id: 'h2', name: 'Alfa', contact_email: '', count: 1 },
    { hospital_id: 'h1', name: 'Zeta', contact_email: 'z@h.co', count: 2 },
  ])
})

test('ignora lo no seleccionado', () => {
  assert.deepEqual(agruparPorHospital(reports, new Set()), [])
})

test('texto de grupo con y sin correo', () => {
  assert.equal(textoGrupo({ count: 2, contact_email: 'z@h.co' }), '2 actas → z@h.co')
  assert.equal(textoGrupo({ count: 1, contact_email: '' }), '1 acta (sin correo de contacto)')
})

test('resumen separa lo que sale de lo que se salta', () => {
  const g = agruparPorHospital(reports, new Set(['a', 'b', 'c']))
  assert.deepEqual(resumenGrupos(g), { conCorreo: 2, sinCorreo: 1 })
})

test('alternar todas marca las visibles y, estando todas, las desmarca', () => {
  const marcadas = alternarTodas(new Set(), reports)
  assert.deepEqual([...marcadas].sort(), ['a', 'b', 'c'])
  assert.equal(todasMarcadas(marcadas, reports), true)
  assert.equal(alternarTodas(marcadas, reports).size, 0)
})

test('alternar todas conserva lo marcado fuera de las visibles', () => {
  const r = alternarTodas(new Set(['otra']), reports.slice(0, 1))
  assert.deepEqual([...r].sort(), ['a', 'otra'])
})
