import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  base64DeDataUrl,
  cargoDelFirmante,
  elegirFirmaGuardada,
  puedeTenerFirmaGuardada,
} from './firmaGuardada.js'

test('solo los usuarios del sistema pueden guardar firma; el hospital no', () => {
  assert.equal(puedeTenerFirmaGuardada('TEC'), true)
  assert.equal(puedeTenerFirmaGuardada('SUP'), true)
  assert.equal(puedeTenerFirmaGuardada('ADMIN'), true)
  assert.equal(puedeTenerFirmaGuardada('CLI'), false)
  assert.equal(puedeTenerFirmaGuardada(undefined), false)
})

test('quita el prefijo de la data URL', () => {
  assert.equal(base64DeDataUrl('data:image/png;base64,AAAA'), 'AAAA')
  assert.equal(base64DeDataUrl('AAAA'), 'AAAA')
  assert.equal(base64DeDataUrl(null), '')
})

test('con respuesta del servidor manda el servidor', () => {
  const remota = { exists: true, image_data: 'data:image/png;base64,SRV' }
  assert.deepEqual(elegirFirmaGuardada({ remota, local: 'data:image/png;base64,TEL' }), {
    dataUrl: 'data:image/png;base64,SRV',
    origen: 'servidor',
  })
})

test('si el servidor dice que no hay firma, no se ofrece la copia del telefono', () => {
  assert.deepEqual(
    elegirFirmaGuardada({ remota: { exists: false }, local: 'data:image/png;base64,TEL' }),
    { dataUrl: null, origen: null }
  )
})

test('sin red se usa la copia del telefono', () => {
  assert.deepEqual(elegirFirmaGuardada({ remota: null, local: 'data:image/png;base64,TEL' }), {
    dataUrl: 'data:image/png;base64,TEL',
    origen: 'telefono',
  })
  assert.deepEqual(elegirFirmaGuardada({ remota: null, local: null }), { dataUrl: null, origen: null })
})

test('cargo por rol', () => {
  assert.equal(cargoDelFirmante('TEC'), 'Técnico')
  assert.equal(cargoDelFirmante('CLI'), '')
})
