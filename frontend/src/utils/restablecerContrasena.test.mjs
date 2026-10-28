import assert from 'node:assert/strict'
import { test } from 'node:test'

import { validarCorreo, validarNuevaContrasena } from './restablecerContrasena.js'

test('validarCorreo pide el correo y revisa el formato', () => {
  assert.deepEqual(validarCorreo(''), { email: 'Ingresa tu correo electrónico.' })
  assert.deepEqual(validarCorreo('   '), { email: 'Ingresa tu correo electrónico.' })
  assert.deepEqual(validarCorreo('abc'), { email: 'El formato del correo no es válido.' })
  assert.deepEqual(validarCorreo(' a@b.co '), {})
})

test('validarNuevaContrasena exige largo y que coincidan', () => {
  assert.deepEqual(validarNuevaContrasena('Abcdef1!', 'Abcdef1!'), {})
  assert.equal(validarNuevaContrasena('corta', 'corta').next, 'Mínimo 8 caracteres.')
  assert.equal(validarNuevaContrasena('Abcdef1!', 'Abcdef1?').confirm, 'Las contraseñas no coinciden.')
  assert.equal(validarNuevaContrasena('', '').next, 'Mínimo 8 caracteres.')
})
