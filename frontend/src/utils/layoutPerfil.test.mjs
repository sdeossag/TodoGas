import assert from 'node:assert/strict'
import { test } from 'node:test'

import { layoutPerfil } from './layoutPerfil.js'

test('el técnico ve Mi perfil dentro de su propio layout', () => {
  assert.equal(layoutPerfil('TEC'), 'tecnico')
})

test('admin y supervisor ven Mi perfil dentro del layout de administración', () => {
  assert.equal(layoutPerfil('ADMIN'), 'administracion')
  assert.equal(layoutPerfil('SUP'), 'administracion')
})

test('la cuenta de hospital (CLI) ve Mi perfil dentro de su propio layout', () => {
  assert.equal(layoutPerfil('CLI'), 'cliente')
})

test('sin rol conocido cae en administración (la puerta ya filtró el acceso)', () => {
  assert.equal(layoutPerfil(undefined), 'administracion')
})
