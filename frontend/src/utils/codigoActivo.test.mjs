import assert from 'node:assert/strict'
import { test } from 'node:test'

import { generarCodigoActivo, sufijoAleatorio, ALFABETO_SUFIJO } from './codigoActivo.js'

// Generador determinista: devuelve los valores en orden, repitiendo el último.
function secuencia(...valores) {
  let i = 0
  return () => valores[Math.min(i++, valores.length - 1)]
}

// Valor en [0, 1) que cae en el símbolo `indice` del alfabeto.
const enIndice = (indice) => (indice + 0.5) / ALFABETO_SUFIJO.length

const FIJO = () => secuencia(enIndice(0), enIndice(1), enIndice(2), enIndice(3), enIndice(4), enIndice(5))
// Índices 0..5 del alfabeto: A B C D E F
const SUFIJO_FIJO = 'ABCDEF'

test('formato basico: hospital, tipo y sufijo separados por un solo guion', () => {
  assert.equal(generarCodigoActivo('SJ1', 'Ventilador', FIJO()), `SJ1-VEN-${SUFIJO_FIJO}`)
})

test('un guion en el codigo del hospital no genera guiones dobles', () => {
  const codigo = generarCodigoActivo('SJ-01', 'Ventilador', FIJO())
  assert.equal(codigo, `SJ0-VEN-${SUFIJO_FIJO}`)
  assert.ok(!codigo.includes('--'), codigo)
})

test('un tipo vacio usa EQP y no deja guiones dobles', () => {
  const codigo = generarCodigoActivo('SJ1', '', FIJO())
  assert.equal(codigo, `SJ1-EQP-${SUFIJO_FIJO}`)
  assert.ok(!codigo.includes('--'), codigo)
})

test('tipo solo con espacios tambien usa EQP', () => {
  assert.equal(generarCodigoActivo('SJ1', '   ', FIJO()), `SJ1-EQP-${SUFIJO_FIJO}`)
})

test('hospital sin codigo usa XXX', () => {
  assert.equal(generarCodigoActivo(undefined, 'Monitor', FIJO()), `XXX-MON-${SUFIJO_FIJO}`)
  assert.equal(generarCodigoActivo('', 'Monitor', FIJO()), `XXX-MON-${SUFIJO_FIJO}`)
})

test('hospital con solo guiones cae al respaldo, sin guiones sobrantes', () => {
  assert.equal(generarCodigoActivo('--', '', FIJO()), `XXX-EQP-${SUFIJO_FIJO}`)
})

test('quita tildes y simbolos del tipo y pasa a mayusculas', () => {
  assert.equal(generarCodigoActivo('hb2', 'Bomba de infusión', FIJO()), `HB2-BOM-${SUFIJO_FIJO}`)
})

test('el sufijo tiene 6 caracteres del alfabeto sin 0, O, 1 ni I', () => {
  assert.equal(ALFABETO_SUFIJO.length, 32)
  for (const excluido of ['0', 'O', '1', 'I']) {
    assert.ok(!ALFABETO_SUFIJO.includes(excluido), excluido)
  }
  const sufijo = sufijoAleatorio(secuencia(0.999999, 0, 0.5, 0.25, 0.75, 0.123))
  assert.equal(sufijo.length, 6)
  for (const c of sufijo) assert.ok(ALFABETO_SUFIJO.includes(c), c)
})

test('un valor de 1 o mas no se sale del alfabeto', () => {
  const sufijo = sufijoAleatorio(() => 1)
  assert.equal(sufijo, '9'.repeat(6))
})

test('dos generaciones con distinto aleatorio dan distinto sufijo', () => {
  const a = generarCodigoActivo('SJ1', 'Monitor', secuencia(0.1))
  const b = generarCodigoActivo('SJ1', 'Monitor', secuencia(0.9))
  assert.notEqual(a, b)
})

test('sin generador inyectado el sufijo es aleatorio del alfabeto', () => {
  const codigo = generarCodigoActivo('SJ1', 'Monitor')
  assert.match(codigo, /^SJ1-MON-[A-HJ-NP-Z2-9]{6}$/)
})

test('sin crypto disponible se usa Math.random como respaldo', () => {
  const original = Object.getOwnPropertyDescriptor(globalThis, 'crypto')
  Object.defineProperty(globalThis, 'crypto', { value: undefined, configurable: true })
  try {
    const codigo = generarCodigoActivo('SJ1', 'Monitor')
    assert.match(codigo, /^SJ1-MON-[A-HJ-NP-Z2-9]{6}$/)
  } finally {
    if (original) Object.defineProperty(globalThis, 'crypto', original)
    else delete globalThis.crypto
  }
})
