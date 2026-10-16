/**
 * Calculos para reducir una foto pesada antes de subirla (PhotoCapture).
 *
 * Es logica pura, sin DOM: el canvas y createImageBitmap viven en
 * compressImage.js y aqui solo se decide a que tamano y con que calidad
 * probar. Se prueba en Node (photoSize.test.mjs).
 */

export const MAX_PHOTO_BYTES = 10 * 1024 * 1024 // el limite del servidor

// Lo que piden los auditores: lado mayor de 4K y JPEG de calidad alta.
export const FIRST_STEP = { maxSide: 3840, quality: 0.85 }

// Hasta donde se esta dispuesto a bajar antes de rendirse. 2048 px sigue
// siendo una foto de equipo legible (placa, manometro); por debajo ya no.
export const MIN_QUALITY = 0.6
export const MIN_SIDE = 2048

const QUALITY_STEP = 0.1
const SIDE_FACTOR = 0.8
const QUALITY_AFTER_RESIZE = 0.8

/** Hasta 10 MB se sube tal cual: no se toca lo que ya cabe. */
export function needsCompression(bytes, limit = MAX_PHOTO_BYTES) {
  return bytes > limit
}

/**
 * Tamano destino: el lado mayor queda en `maxSide` y se conserva la
 * proporcion. Nunca agranda una foto que ya es mas pequena.
 */
export function targetDimensions(width, height, maxSide) {
  const largest = Math.max(width, height)
  if (!(largest > 0)) return { width: 0, height: 0 }
  if (largest <= maxSide) return { width, height }
  const scale = maxSide / largest
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  }
}

/**
 * Siguiente intento cuando el anterior todavia pesa de mas: primero baja la
 * calidad, y si ya esta en el piso reduce el tamano y vuelve a subir la
 * calidad. Devuelve null cuando no queda nada razonable por probar.
 */
export function nextStep({ maxSide, quality }) {
  const lowerQuality = Math.round((quality - QUALITY_STEP) * 100) / 100
  if (lowerQuality >= MIN_QUALITY) return { maxSide, quality: lowerQuality }

  const smallerSide = Math.round(maxSide * SIDE_FACTOR)
  if (smallerSide >= MIN_SIDE) return { maxSide: smallerSide, quality: QUALITY_AFTER_RESIZE }

  return null
}

/** Nombre del JPEG resultante: mismo nombre, extension .jpg. */
export function jpegName(name = 'foto') {
  const base = name.replace(/\.[^./\\]+$/, '') || 'foto'
  return `${base}.jpg`
}

/** "14,2 MB" para mostrarle el antes y el despues al tecnico. */
export function formatMB(bytes) {
  return `${(bytes / (1024 * 1024)).toFixed(1).replace('.', ',')} MB`
}
