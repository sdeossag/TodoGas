import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  ACCION_BAJA,
  ACCION_REACTIVAR,
  INICIO_HOY,
  INICIO_ULTIMO_CIERRE,
  MAX_ACTIVOS_MASIVO,
  OPCIONES_INICIO,
  alternarTodas,
  excedeLimite,
  textoCambian,
  textoOts,
  textoResultado,
  textoSeleccion,
  textoTareas,
  textoTareasHechas,
  tituloAccion,
  todasMarcadas,
  validarSeleccion,
} from './estadoMasivo.js'

const filas = [{ id: 'a' }, { id: 'b' }, { id: 'c' }]

test('el límite es el del servidor', () => {
  assert.equal(MAX_ACTIVOS_MASIVO, 200)
  assert.equal(excedeLimite(200), false)
  assert.equal(excedeLimite(201), true)
})

test('validarSeleccion pide al menos uno y respeta el límite', () => {
  assert.match(validarSeleccion(0), /al menos un activo/)
  assert.equal(validarSeleccion(1), null)
  assert.equal(validarSeleccion(200), null)
  assert.match(validarSeleccion(201), /200 activos/)
})

test('textoSeleccion singular y plural', () => {
  assert.equal(textoSeleccion(1), '1 activo seleccionado')
  assert.equal(textoSeleccion(5), '5 activos seleccionados')
})

test('alternarTodas marca las visibles y las desmarca, sin tocar otras páginas', () => {
  const marcada = alternarTodas(new Set(['otra-pagina']), filas)
  assert.deepEqual([...marcada].sort(), ['a', 'b', 'c', 'otra-pagina'])
  assert.equal(todasMarcadas(marcada, filas), true)
  const vacia = alternarTodas(marcada, filas)
  assert.deepEqual([...vacia], ['otra-pagina'])
  assert.equal(todasMarcadas(new Set(['a']), filas), false)
  assert.equal(todasMarcadas(new Set(), []), false)
  assert.deepEqual([...alternarTodas(new Set(['a']), filas)].sort(), ['a', 'b', 'c'])
})

test('tituloAccion', () => {
  assert.equal(tituloAccion(ACCION_BAJA), 'Dar de baja')
  assert.equal(tituloAccion(ACCION_REACTIVAR), 'Reactivar')
})

test('textoCambian cuenta lo que cambia y lo que ya estaba', () => {
  assert.equal(textoCambian({ changed: 3, unchanged: 0 }, ACCION_BAJA), '3 activos: se darán de baja.')
  assert.equal(textoCambian({ changed: 1, unchanged: 2 }, ACCION_REACTIVAR),
    '1 activo: se reactivará. 2 ya están activo y no cambian.')
  assert.equal(textoCambian({ changed: 0, unchanged: 1 }, ACCION_BAJA),
    'Ningún activo cambia de estado. 1 ya está de baja y no cambia.')
})

test('textoTareas de la baja habla de anular, de la reactivación de abrir', () => {
  assert.match(textoTareas({ cancelled: 0 }, ACCION_BAJA), /No hay tareas pendientes/)
  assert.match(textoTareas({ cancelled: 1 }, ACCION_BAJA), /Se anulará 1 tarea/)
  assert.match(textoTareas({ cancelled: 4 }, ACCION_BAJA), /Se anularán 4 tareas/)
  assert.match(textoTareas({ reopened: 6 }, ACCION_REACTIVAR, INICIO_HOY), /Se abrirán 6 tareas.*para hoy/)
  assert.match(textoTareas({ reopened: 1 }, ACCION_REACTIVAR, INICIO_ULTIMO_CIERRE), /1 tarea.*último mantenimiento/)
  assert.match(textoTareas({ reopened: 0 }, ACCION_REACTIVAR), /No hay tareas del protocolo/)
})

test('textoOts avisa solo si hay OT abiertas', () => {
  assert.equal(textoOts({ in_work_orders: [] }), null)
  assert.equal(textoOts({}), null)
  assert.match(textoOts({ in_work_orders: ['OT-1'] }), /1 OT abierta conserva.*OT-1/)
  assert.match(textoOts({ in_work_orders: ['OT-1', 'OT-2'] }), /2 OT abiertas conservan/)
})

test('textoResultado', () => {
  assert.equal(textoResultado({ changed: 2, unchanged: 0 }, ACCION_BAJA), '2 activos dados de baja.')
  assert.equal(textoResultado({ changed: 1, unchanged: 1 }, ACCION_REACTIVAR),
    '1 activo reactivado. 1 ya estaba en ese estado.')
  assert.equal(textoResultado({ changed: 0, unchanged: 3 }, ACCION_BAJA), 'No hubo cambios. 3 ya estaban en ese estado.')
})

test('la reactivación ofrece primero "desde hoy"', () => {
  assert.equal(OPCIONES_INICIO[0].value, INICIO_HOY)
  assert.match(OPCIONES_INICIO[0].label, /recomendado/)
  assert.equal(OPCIONES_INICIO[1].value, INICIO_ULTIMO_CIERRE)
})

test('textoTareasHechas habla en pasado', () => {
  assert.equal(textoTareasHechas({ cancelled: 2 }, ACCION_BAJA), '2 tareas pendientes anuladas.')
  assert.equal(textoTareasHechas({ cancelled: 0 }, ACCION_BAJA), 'No había tareas pendientes que anular.')
  assert.equal(textoTareasHechas({ reopened: 1 }, ACCION_REACTIVAR, INICIO_HOY),
    '1 tarea del protocolo abierta, programadas para hoy.')
})
