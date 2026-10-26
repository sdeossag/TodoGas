import assert from 'node:assert/strict'
import { test } from 'node:test'

import { aInputLocal, validarIntervencion } from './intervencion.js'

const AHORA = new Date('2026-10-16T12:00:00').getTime()
const CREADA = '2026-10-10T08:00:00'

test('una ventana pasada y ordenada no tiene errores', () => {
  assert.deepEqual(validarIntervencion('2026-10-15T09:00', '2026-10-15T10:00', CREADA, AHORA), {})
})

test('el fin antes del inicio se marca en el fin', () => {
  const e = validarIntervencion('2026-10-15T10:00', '2026-10-15T09:00', CREADA, AHORA)
  assert.match(e.end, /antes del inicio/)
  assert.equal(e.start, undefined)
})

test('no acepta el futuro, con 5 minutos de tolerancia', () => {
  assert.equal(validarIntervencion('2026-10-16T11:00', '2026-10-16T12:04', CREADA, AHORA).end, undefined)
  assert.match(validarIntervencion('2026-10-16T11:00', '2026-10-16T12:30', CREADA, AHORA).end, /futuro/)
})

test('no acepta una fecha anterior a la creación de la orden', () => {
  assert.match(validarIntervencion('2026-10-01T09:00', '2026-10-15T10:00', CREADA, AHORA).start, /creara/)
})

test('pide las dos fechas', () => {
  const e = validarIntervencion('', '', CREADA, AHORA)
  assert.ok(e.start && e.end)
})

test('aInputLocal devuelve vacío sin fecha y formato datetime-local con fecha', () => {
  assert.equal(aInputLocal(null), '')
  assert.match(aInputLocal('2026-10-15T14:30:00Z'), /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/)
})
