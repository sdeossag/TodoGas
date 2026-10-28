import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  botonDeshabilitado,
  haceCuanto,
  mensajeResultado,
  textoBoton,
  textoUltimaSincronizacion,
} from './sincronizarAhora.js'

const base = new Date('2026-10-28T12:00:00Z').getTime()
const antes = (ms) => new Date(base - ms).toISOString()

test('haceCuanto formatea minutos, horas y dias', () => {
  assert.equal(haceCuanto(null, base), null)
  assert.equal(haceCuanto('basura', base), null)
  assert.equal(haceCuanto(antes(10_000), base), 'hace un momento')
  assert.equal(haceCuanto(antes(3 * 60_000), base), 'hace 3 min')
  assert.equal(haceCuanto(antes(2 * 3600_000), base), 'hace 2 h')
  assert.equal(haceCuanto(antes(24 * 3600_000), base), 'hace 1 dia')
  assert.equal(haceCuanto(antes(72 * 3600_000), base), 'hace 3 dias')
  assert.equal(haceCuanto(antes(-5000), base), 'hace un momento')
})

test('textoUltimaSincronizacion', () => {
  assert.equal(textoUltimaSincronizacion(antes(5 * 60_000), base), 'Última sincronización: hace 5 min')
  assert.match(textoUltimaSincronizacion(null, base), /Aún no/)
})

test('textoBoton y botonDeshabilitado', () => {
  assert.equal(textoBoton({ isOnline: true, isSyncing: false }), 'Sincronizar ahora')
  assert.equal(textoBoton({ isOnline: true, isSyncing: true }), 'Sincronizando…')
  assert.equal(textoBoton({ isOnline: false, isSyncing: false }), 'Sin conexión')
  assert.equal(botonDeshabilitado({ isOnline: false, isSyncing: false }), true)
  assert.equal(botonDeshabilitado({ isOnline: true, isSyncing: true }), true)
  assert.equal(botonDeshabilitado({ isOnline: true, isSyncing: false }), false)
})

test('mensajeResultado', () => {
  assert.deepEqual(mensajeResultado({ error: 'timeout' }), {
    tipo: 'error',
    texto: 'No se pudo sincronizar: timeout',
  })
  assert.equal(mensajeResultado({ pendientes: 1 }).texto, 'Quedan 1 elemento por enviar')
  assert.equal(mensajeResultado({ pendientes: 4 }).tipo, 'aviso')
  assert.deepEqual(mensajeResultado({}), { tipo: 'ok', texto: 'Todo al día' })
})
