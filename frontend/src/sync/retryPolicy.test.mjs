import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  BACKOFF_BASE_MS,
  BACKOFF_MAX_MS,
  PERMANENT,
  STATUS_ATTENTION,
  STATUS_RETRY,
  TRANSIENT,
  backoffDelayMs,
  classifyError,
  dueNow,
  isChecklistCompleted,
  itemLabel,
  nextState,
  serverMessage,
} from './retryPolicy.js'

const http = (status, data = {}) => ({ isAxiosError: true, response: { status, data } })
const red = { isAxiosError: true, request: {}, code: 'ERR_NETWORK', message: 'Network Error' }

test('sin respuesta, 5xx, 408, 429 y 401 son transitorios', () => {
  assert.equal(classifyError(red).kind, TRANSIENT)
  for (const s of [500, 502, 503, 408, 429, 401]) {
    assert.equal(classifyError(http(s)).kind, TRANSIENT, String(s))
  }
})

test('los otros 4xx son permanentes', () => {
  for (const s of [400, 403, 404, 409, 413, 422]) {
    assert.equal(classifyError(http(s)).kind, PERMANENT, String(s))
  }
  assert.equal(classifyError(http(400)).status, 400)
})

test('un error local, sin red de por medio, no se reintenta solo', () => {
  assert.equal(classifyError(new Error('Ruta de foto no soportada')).kind, PERMANENT)
})

test('la espera dobla en cada fallo y topa en 30 minutos', () => {
  const medio = () => 0.5 // sin jitter
  assert.equal(backoffDelayMs(1, medio), BACKOFF_BASE_MS)
  assert.equal(backoffDelayMs(2, medio), 2 * BACKOFF_BASE_MS)
  assert.equal(backoffDelayMs(3, medio), 4 * BACKOFF_BASE_MS)
  assert.equal(backoffDelayMs(6, medio), 30 * 60 * 1000) // 32 min -> tope
  assert.equal(backoffDelayMs(50, medio), BACKOFF_MAX_MS)
})

test('el jitter queda dentro de +-25% y nunca pasa el tope', () => {
  assert.equal(backoffDelayMs(2, () => 0), Math.round(0.75 * 2 * BACKOFF_BASE_MS))
  assert.equal(backoffDelayMs(2, () => 0.999), Math.round(1.2495 * 2 * BACKOFF_BASE_MS))
  assert.ok(backoffDelayMs(20, () => 0.999) <= BACKOFF_MAX_MS)
})

test('nextState: transitorio agenda, permanente pide atencion', () => {
  const ahora = 1_000_000
  const a = nextState(null, red, ahora, () => 0.5)
  assert.deepEqual(a, { status: STATUS_RETRY, attempts: 1, next_retry_at: ahora + BACKOFF_BASE_MS, http_status: null })

  const b = nextState({ attempts: 1 }, http(503), ahora, () => 0.5)
  assert.equal(b.attempts, 2)
  assert.equal(b.next_retry_at, ahora + 2 * BACKOFF_BASE_MS)

  const c = nextState({ attempts: 2 }, http(400), ahora)
  assert.deepEqual(c, { status: STATUS_ATTENTION, attempts: 3, next_retry_at: null, http_status: 400 })
})

test('dueNow: sin estado toca; en espera no; atencion nunca', () => {
  assert.equal(dueNow(undefined, 100), true)
  assert.equal(dueNow({ status: STATUS_RETRY, next_retry_at: 200 }, 100), false)
  assert.equal(dueNow({ status: STATUS_RETRY, next_retry_at: 100 }, 100), true)
  assert.equal(dueNow({ status: STATUS_RETRY, next_retry_at: null }, 100), true)
  assert.equal(dueNow({ status: STATUS_ATTENTION, next_retry_at: null }, 100), false)
})

test('mensaje del servidor legible, nunca HTML', () => {
  assert.equal(serverMessage(http(400, { detail: 'El checklist no admite cambios.' })), 'El checklist no admite cambios.')
  assert.equal(serverMessage(http(400, { value: ['Obligatorio.', 'Revisa.'] })), 'Obligatorio. Revisa.')
  assert.equal(serverMessage(http(502, '<html><body>Bad gateway</body></html>')), 'El servidor respondió con el error 502.')
  assert.equal(serverMessage(red), 'Network Error')
})

test('checklist ya completado: por codigo, y por texto en servidores viejos', () => {
  assert.equal(isChecklistCompleted(http(400, { code: 'checklist_completed', detail: 'otro texto' })), true)
  assert.equal(isChecklistCompleted(http(400, { detail: 'El checklist ya está completado.' })), true)
  assert.equal(isChecklistCompleted(http(400, { detail: 'Falta un campo.' })), false)
  assert.equal(isChecklistCompleted(http(500, { code: 'checklist_completed' })), false)
  assert.equal(isChecklistCompleted(red), false)
})

test('etiquetas en lenguaje claro', () => {
  assert.equal(itemLabel('photo'), 'Una foto')
  assert.equal(itemLabel('raro'), 'Un dato')
})
