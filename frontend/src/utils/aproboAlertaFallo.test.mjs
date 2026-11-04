import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  allowsNa, answerLabel, getFieldType, NEW_FIELD_TYPES, passAlertFailLabel, passAlertFailOptions,
} from '../constants/checklistFields.js'

const conNa = { field_type: 'PASS_ALERT_FAIL', options_json: { allow_na: true } }
const sinNa = { field_type: 'PASS_ALERT_FAIL', options_json: [] }

test('el tipo se puede elegir en el editor', () => {
  assert.ok(NEW_FIELD_TYPES.some((t) => t.value === 'PASS_ALERT_FAIL'))
  assert.equal(getFieldType('PASS_ALERT_FAIL').label, 'Aprobó / Alerta / Falló')
})

test('N/A solo aparece si el campo lo permite', () => {
  assert.equal(allowsNa(conNa), true)
  assert.equal(allowsNa(sinNa), false)
  assert.deepEqual(passAlertFailOptions(conNa), ['APROBO', 'ALERTA', 'FALLO', 'NA'])
  assert.deepEqual(passAlertFailOptions(sinNa), ['APROBO', 'ALERTA', 'FALLO'])
})

test('etiquetas en español', () => {
  assert.equal(passAlertFailLabel('APROBO'), 'Aprobó')
  assert.equal(passAlertFailLabel('ALERTA'), 'Alerta')
  assert.equal(passAlertFailLabel('FALLO'), 'Falló')
  assert.equal(passAlertFailLabel('NA'), 'N/A')
  assert.equal(answerLabel(conNa, 'FALLO'), 'Falló')
  assert.equal(answerLabel({ field_type: 'BOOLEAN' }, 'false'), 'No')
  assert.equal(answerLabel({ field_type: 'TEXT' }, 'hola'), 'hola')
})
