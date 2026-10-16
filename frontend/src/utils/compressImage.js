/**
 * Reduce en el navegador una foto que pesa mas del limite. Los calculos
 * (tamano destino, siguiente paso) estan en photoSize.js; aqui solo esta lo
 * que necesita DOM.
 */

import { FIRST_STEP, MAX_PHOTO_BYTES, jpegName, nextStep, targetDimensions } from './photoSize'

/**
 * Decodifica respetando la orientacion EXIF: sin eso una foto vertical tomada
 * con el celular saldria acostada al pasar por el canvas.
 */
async function decode(file) {
  if (typeof createImageBitmap === 'function') {
    try {
      return await createImageBitmap(file, { imageOrientation: 'from-image' })
    } catch {
      // Navegadores que no aceptan la opcion: se prueba con <img>, que aplica
      // la orientacion por si solo.
    }
  }
  const url = URL.createObjectURL(file)
  try {
    const img = new Image()
    img.src = url
    await img.decode()
    return img
  } finally {
    URL.revokeObjectURL(url)
  }
}

const sizeOf = (source) => ({
  width: source.naturalWidth ?? source.width,
  height: source.naturalHeight ?? source.height,
})

function toJpeg(canvas, quality) {
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality))
}

/**
 * Devuelve un File JPEG de hasta `limit` bytes, o lanza si ni el ultimo paso
 * de la escalera lo logra. `onStep` avisa cuando hace falta un intento mas.
 */
export async function compressImage(file, { limit = MAX_PHOTO_BYTES, onStep } = {}) {
  const source = await decode(file)
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  const original = sizeOf(source)

  try {
    let step = FIRST_STEP
    let intentos = 0
    while (step) {
      const { width, height } = targetDimensions(original.width, original.height, step.maxSide)
      canvas.width = width
      canvas.height = height
      // Un PNG con transparencia sin fondo saldria negro en JPEG.
      ctx.fillStyle = '#fff'
      ctx.fillRect(0, 0, width, height)
      ctx.drawImage(source, 0, 0, width, height)

      const blob = await toJpeg(canvas, step.quality)
      if (blob && blob.size <= limit) {
        return new File([blob], jpegName(file.name), { type: 'image/jpeg', lastModified: Date.now() })
      }
      step = nextStep(step)
      intentos += 1
      if (step) onStep?.(intentos)
    }
    throw new Error('demasiado-pesada')
  } finally {
    source.close?.()
    // Suelta la memoria del canvas: en el telefono son decenas de MB.
    canvas.width = 0
    canvas.height = 0
  }
}
