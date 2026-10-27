import assert from 'node:assert/strict'
import { test } from 'node:test'

import { avisoFechaInicio, cuerpoAsignacion, hoyISO, versionPredeterminada } from './inicioProtocolo.js'

test('la fecha vacía no viaja en el cuerpo', () => {
  assert.deepEqual(cuerpoAsignacion('asset_ids', ['a'], ''), { asset_ids: ['a'] })
  assert.deepEqual(cuerpoAsignacion('asset_ids', ['a'], undefined), { asset_ids: ['a'] })
  assert.deepEqual(cuerpoAsignacion('node_ids', ['n'], '2026-10-24'), {
    node_ids: ['n'], start_date: '2026-10-24',
  })
})

test('hoy se toma en hora local', () => {
  assert.equal(hoyISO(new Date(2026, 9, 5, 23, 59)), '2026-10-05')
})

test('avisa si la fecha es pasada o es hoy, y calla si es futura o vacía', () => {
  assert.match(avisoFechaInicio('2026-10-20', '2026-10-27'), /vencida/)
  assert.match(avisoFechaInicio('2026-10-27', '2026-10-27'), /hoy/)
  assert.equal(avisoFechaInicio('2026-11-01', '2026-10-27'), null)
  assert.equal(avisoFechaInicio('', '2026-10-27'), null)
})

test('preselecciona la versión vigente de la plantilla predeterminada', () => {
  const plantillas = [
    { id: 't1', current_version_id: 'v1' },
    { id: 't2', current_version_id: null },
  ]
  assert.equal(versionPredeterminada({ default_checklist_template: 't1' }, plantillas), 'v1')
  assert.equal(versionPredeterminada({ default_checklist_template: 't2' }, plantillas), '')
  assert.equal(versionPredeterminada({ default_checklist_template: 'x' }, plantillas), '')
  assert.equal(versionPredeterminada({ default_checklist_template: null }, plantillas), '')
  assert.equal(versionPredeterminada({}, undefined), '')
})
