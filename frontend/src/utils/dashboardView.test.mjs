import assert from 'node:assert/strict'
import test from 'node:test'

import { assetsLink, monthLabel, monthRange, pendingTasksLink, shares } from './dashboardView.js'

test('monthLabel abrevia el mes en español', () => {
  assert.deepEqual(monthLabel('2026-10'), { short: 'Oct', long: 'Oct 2026' })
})

test('monthRange cubre el mes completo, febrero bisiesto incluido', () => {
  assert.deepEqual(monthRange('2028-02'), { from: '2028-02-01', to: '2028-02-29' })
  assert.deepEqual(monthRange('2026-12'), { from: '2026-12-01', to: '2026-12-31' })
})

test('las vencidas llevan overdue y un mes lleva su rango', () => {
  assert.equal(pendingTasksLink({ ym: null }), '/tareas-pendientes?overdue=1')
  assert.equal(
    pendingTasksLink({ ym: '2026-11', hospitalId: 'h1', today: '2026-10-16' }),
    '/tareas-pendientes?hospital_id=h1&due_after=2026-11-01&due_before=2026-11-30'
  )
})

test('el mes en curso empieza hoy, porque lo anterior ya está en vencidas', () => {
  assert.equal(
    pendingTasksLink({ ym: '2026-10', today: '2026-10-16' }),
    '/tareas-pendientes?due_after=2026-10-16&due_before=2026-10-31'
  )
})

test('assetsLink pasa el estado y el hospital', () => {
  assert.equal(assetsLink('overdue', 'h1'), '/activos?maintenance_status=overdue&hospital_id=h1')
  assert.equal(assetsLink('no_plan'), '/activos?maintenance_status=no_plan')
})

test('shares omite lo que vale cero y suma 100', () => {
  const r = shares([{ value: 3 }, { value: 0 }, { value: 1 }])
  assert.equal(r.length, 2)
  assert.equal(r[0].pct, 75)
  assert.deepEqual(shares([{ value: 0 }]), [])
})
