import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  claveLocal,
  estadoDelAviso,
  guardarAceptadaLocal,
  leerAceptadaLocal,
  nombreArchivoDatos,
} from './consentimiento.js'
import { PARRAFOS, TITULO, VERSION } from '../legal/avisoPrivacidad.js'

const V = '2026-10-28'

test('el servidor manda: requerido pide, no requerido permite', () => {
  assert.equal(estadoDelAviso({ datos: { required: true }, versionApp: V }), 'pedir')
  assert.equal(estadoDelAviso({ datos: { required: false }, versionApp: V }), 'permitir')
  // aunque localmente conste otra cosa
  assert.equal(
    estadoDelAviso({ datos: { required: true }, aceptadaLocal: V, versionApp: V }),
    'pedir'
  )
})

test('sin respuesta del servidor no se bloquea', () => {
  assert.equal(estadoDelAviso({ error: new Error('Network Error'), versionApp: V }), 'permitir')
  assert.equal(
    estadoDelAviso({ error: { response: { status: 500 } }, aceptadaLocal: null, versionApp: V }),
    'permitir'
  )
})

test('mientras carga: con constancia local de esta version pasa, sin ella espera', () => {
  assert.equal(estadoDelAviso({ cargando: true, aceptadaLocal: V, versionApp: V }), 'permitir')
  assert.equal(estadoDelAviso({ cargando: true, aceptadaLocal: '2025-01-01', versionApp: V }), 'esperar')
  assert.equal(estadoDelAviso({ cargando: true, aceptadaLocal: null, versionApp: V }), 'esperar')
})

test('la constancia local se guarda por usuario y version', () => {
  const mem = new Map()
  const storage = { getItem: (k) => mem.get(k) ?? null, setItem: (k, v) => mem.set(k, v) }
  assert.equal(leerAceptadaLocal('u1', storage), null)
  guardarAceptadaLocal('u1', V, storage)
  assert.equal(leerAceptadaLocal('u1', storage), V)
  assert.equal(leerAceptadaLocal('u2', storage), null)
  assert.equal(claveLocal('u1'), 'todogas.privacidad.u1')
})

test('un almacenamiento que falla no rompe nada', () => {
  const roto = {
    getItem: () => {
      throw new Error('bloqueado')
    },
    setItem: () => {
      throw new Error('bloqueado')
    },
  }
  assert.equal(leerAceptadaLocal('u1', roto), null)
  assert.doesNotThrow(() => guardarAceptadaLocal('u1', V, roto))
})

test('nombre del archivo de datos personales', () => {
  assert.equal(
    nombreArchivoDatos(new Date('2026-10-28T12:00:00Z')),
    'mis-datos-personales-2026-10-28.json'
  )
})

test('el aviso: version, titulo, marcadores y extension razonable', () => {
  assert.match(VERSION, /^\d{4}-\d{2}-\d{2}$/)
  assert.ok(TITULO.length > 0)
  const texto = PARRAFOS.join(' ')
  for (const m of ['[RAZÓN SOCIAL]', '[NIT]', '[CORREO DE CONTACTO]']) assert.ok(texto.includes(m), m)
  for (const clave of ['SIC', 'GPS', 'firma', 'supresión', 'auditoría']) {
    assert.ok(texto.includes(clave), clave)
  }
  const palabras = texto.split(/\s+/).length
  assert.ok(palabras >= 150 && palabras <= 250, `palabras: ${palabras}`)
})
