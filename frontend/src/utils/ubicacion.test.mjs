import assert from 'node:assert/strict'
import { test } from 'node:test'

import { distanciaMetros, textoDistancia, rutaLegible, textoOrigen } from './ubicacion.js'

test('la distancia entre el mismo punto es cero', () => {
  assert.equal(Math.round(distanciaMetros({ lat: 6.2442, lng: -75.5812 }, { lat: 6.2442, lng: -75.5812 })), 0)
})

test('0.001 grados de latitud son unos 111 metros', () => {
  const m = distanciaMetros({ lat: 6.2442, lng: -75.5812 }, { lat: 6.2452, lng: -75.5812 })
  assert.ok(m > 108 && m < 114, String(m))
})

test('la distancia acepta numeros en texto, como los manda el servidor', () => {
  const m = distanciaMetros({ lat: '6.2442', lng: '-75.5812' }, { lat: 6.2452, lng: -75.5812 })
  assert.ok(m > 108 && m < 114)
})

test('sin alguno de los puntos no hay distancia', () => {
  assert.equal(distanciaMetros(null, { lat: 1, lng: 1 }), null)
  assert.equal(distanciaMetros({ lat: 1, lng: 1 }, { lat: null, lng: 1 }), null)
})

test('la frase habla en lenguaje claro', () => {
  assert.equal(textoDistancia(3), 'Tomado en la ubicación registrada')
  assert.equal(textoDistancia(40.4), 'Tomado a 40 m de la ubicación registrada')
  assert.equal(textoDistancia(1250), 'Tomado a 1,3 km de la ubicación registrada')
  assert.equal(textoDistancia(null), '')
})

test('la ruta legible lleva el hospital y separa con flechas', () => {
  assert.equal(
    rutaLegible('Clínica Demo Norte', 'Bloque A/Piso 1/Urgencias'),
    'Clínica Demo Norte › Bloque A › Piso 1 › Urgencias'
  )
  assert.equal(rutaLegible('H', ''), 'H')
  assert.equal(rutaLegible('', 'Bloque A'), 'Bloque A')
})

test('el origen se dice en una frase', () => {
  assert.equal(textoOrigen({ kind: 'own', label: 'propio' }), 'Punto propio de esta ubicación')
  assert.equal(textoOrigen({ kind: 'inherited', name: 'Piso 1', label: 'heredado de Piso 1' }), 'Punto heredado de Piso 1')
  assert.equal(textoOrigen(null), '')
})
