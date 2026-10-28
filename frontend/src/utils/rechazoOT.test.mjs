import assert from 'node:assert/strict'
import { test } from 'node:test'

import { ultimoRechazo } from './rechazoOT.js'

const cambio = (from, to, extra = {}) => ({
  from_status: from,
  to_status: to,
  comment: '',
  changed_by: { full_name: 'Ana Supervisora' },
  changed_at: '2026-10-28T15:00:00Z',
  ...extra,
})

test('rechazo vigente: OT en curso y último cambio de revisión a en curso', () => {
  const ot = {
    status: 'IN_PROGRESS',
    status_history: [
      cambio('PENDING', 'IN_PROGRESS', { changed_at: '2026-10-27T10:00:00Z' }),
      cambio('IN_PROGRESS', 'IN_REVIEW', { changed_at: '2026-10-27T12:00:00Z' }),
      cambio('IN_REVIEW', 'IN_PROGRESS', { comment: 'Falta la foto del manómetro' }),
    ],
  }
  assert.deepEqual(ultimoRechazo(ot), {
    motivo: 'Falta la foto del manómetro',
    por: 'Ana Supervisora',
    fecha: '2026-10-28T15:00:00Z',
  })
})

test('si volvió a revisión ya no aplica', () => {
  const ot = {
    status: 'IN_REVIEW',
    status_history: [
      cambio('IN_REVIEW', 'IN_PROGRESS', { comment: 'x' }),
      cambio('IN_PROGRESS', 'IN_REVIEW', { changed_at: '2026-10-28T16:00:00Z' }),
    ],
  }
  assert.equal(ultimoRechazo(ot), null)
})

test('no depende del orden del arreglo', () => {
  const ot = {
    status: 'IN_PROGRESS',
    status_history: [
      cambio('IN_REVIEW', 'IN_PROGRESS', { comment: 'corrige' }),
      cambio('IN_PROGRESS', 'IN_REVIEW', { changed_at: '2026-10-28T14:00:00Z' }),
    ],
  }
  assert.equal(ultimoRechazo(ot).motivo, 'corrige')
})

test('sin historial, en otro estado o sin OT: null', () => {
  assert.equal(ultimoRechazo(null), null)
  assert.equal(ultimoRechazo({ status: 'IN_PROGRESS', status_history: [] }), null)
  assert.equal(ultimoRechazo({ status: 'IN_PROGRESS' }), null)
  assert.equal(
    ultimoRechazo({ status: 'COMPLETED', status_history: [cambio('IN_REVIEW', 'IN_PROGRESS')] }),
    null,
  )
  assert.equal(
    ultimoRechazo({ status: 'IN_PROGRESS', status_history: [cambio('PENDING', 'IN_PROGRESS')] }),
    null,
  )
})

test('la lista trae last_rejection en vez del historial', () => {
  const r = { motivo: 'm', por: 'p', fecha: '2026-10-28T15:00:00Z' }
  assert.deepEqual(ultimoRechazo({ status: 'IN_PROGRESS', last_rejection: r }), r)
  assert.equal(ultimoRechazo({ status: 'IN_REVIEW', last_rejection: r }), null)
})
