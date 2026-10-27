import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  esErrorFirmaRequerida,
  estadoDialogoAprobar,
  mensajeFirmaRequerida,
} from './aprobarFirma.js'

const errorDelServidor = (data) => ({ response: { status: 400, data } })

test('reconoce el error de firma requerida por su codigo', () => {
  const err = errorDelServidor({ code: 'firma_requerida', detail: 'Registra tu firma.' })
  assert.equal(esErrorFirmaRequerida(err), true)
  assert.equal(esErrorFirmaRequerida(errorDelServidor({ detail: 'Otro error' })), false)
  assert.equal(esErrorFirmaRequerida(new Error('red caida')), false)
  assert.equal(esErrorFirmaRequerida(undefined), false)
})

test('muestra el detail del servidor o un texto por defecto', () => {
  const conDetalle = errorDelServidor({ code: 'firma_requerida', detail: '  Firma borrada.  ' })
  assert.equal(mensajeFirmaRequerida(conDetalle), 'Firma borrada.')
  const sinDetalle = errorDelServidor({ code: 'firma_requerida' })
  assert.equal(
    mensajeFirmaRequerida(sinDetalle),
    'Registra tu firma en Mi perfil para aprobar esta orden.'
  )
})

test('con firma guardada: se firma y se puede aprobar', () => {
  const estado = estadoDialogoAprobar({ cargando: false, dataUrl: 'data:image/png;base64,AAAA' })
  assert.equal(estado.tipo, 'con_firma')
  assert.equal(estado.puedeAprobar, true)
  assert.equal(estado.texto, 'Se firmará con tu firma guardada')
  assert.equal(estado.textoBoton, 'Aprobar y firmar')
})

test('sin firma guardada: no se puede aprobar y se ofrece Mi perfil', () => {
  const estado = estadoDialogoAprobar({ cargando: false, dataUrl: null })
  assert.equal(estado.tipo, 'sin_firma')
  assert.equal(estado.puedeAprobar, false)
  assert.equal(estado.texto, 'Para aprobar necesitas registrar tu firma')
  assert.ok(estado.textoEnlace)
})

test('mientras se consulta la firma no se puede aprobar', () => {
  const estado = estadoDialogoAprobar({ cargando: true, dataUrl: null })
  assert.equal(estado.tipo, 'cargando')
  assert.equal(estado.puedeAprobar, false)
})
