import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  FIRST_STEP,
  MAX_PHOTO_BYTES,
  MIN_QUALITY,
  MIN_SIDE,
  formatMB,
  jpegName,
  needsCompression,
  nextStep,
  targetDimensions,
} from './photoSize.js'

test('hasta 10 MB se sube tal cual', () => {
  assert.equal(needsCompression(MAX_PHOTO_BYTES), false)
  assert.equal(needsCompression(1024), false)
  assert.equal(needsCompression(MAX_PHOTO_BYTES + 1), true)
})

test('el lado mayor queda en el maximo y se conserva la proporcion', () => {
  assert.deepEqual(targetDimensions(8000, 6000, 3840), { width: 3840, height: 2880 })
  assert.deepEqual(targetDimensions(6000, 8000, 3840), { width: 2880, height: 3840 })
})

test('una foto mas pequena que el maximo no se agranda', () => {
  assert.deepEqual(targetDimensions(3000, 2000, 3840), { width: 3000, height: 2000 })
  assert.deepEqual(targetDimensions(3840, 100, 3840), { width: 3840, height: 100 })
})

test('dimensiones invalidas no revientan', () => {
  assert.deepEqual(targetDimensions(0, 0, 3840), { width: 0, height: 0 })
  assert.deepEqual(targetDimensions(10000, 1, 3840), { width: 3840, height: 1 })
})

test('primero baja la calidad, despues el tamano', () => {
  assert.deepEqual(nextStep(FIRST_STEP), { maxSide: 3840, quality: 0.75 })
  assert.deepEqual(nextStep({ maxSide: 3840, quality: 0.65 }), { maxSide: 3072, quality: 0.8 })
})

test('la escalera termina, siempre empeora y respeta los pisos', () => {
  let paso = FIRST_STEP
  let pasos = 0
  while (true) {
    const siguiente = nextStep(paso)
    if (!siguiente) break
    assert.ok(
      siguiente.maxSide < paso.maxSide || siguiente.quality < paso.quality,
      'cada paso tiene que reducir algo'
    )
    assert.ok(siguiente.quality >= MIN_QUALITY)
    assert.ok(siguiente.maxSide >= MIN_SIDE)
    paso = siguiente
    pasos += 1
    assert.ok(pasos < 50, 'no termina')
  }
  assert.ok(pasos >= 3)
})

test('nombre y tamano legibles', () => {
  assert.equal(jpegName('IMG_0001.HEIC'), 'IMG_0001.jpg')
  assert.equal(jpegName('sin-extension'), 'sin-extension.jpg')
  assert.equal(jpegName(''), 'foto.jpg')
  assert.equal(formatMB(14.2 * 1024 * 1024), '14,2 MB')
})
