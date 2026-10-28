/**
 * Genera un código sugerido para un activo: CODIGO_HOSPITAL-TIPO-SUFIJO.
 *
 * El código no tiene formato de negocio (es para Fracttal); solo debe ser
 * único y legible. El servidor valida la unicidad (AssetCreateUpdateSerializer).
 *
 * Cada parte se limpia antes de usarse: sin tildes, solo letras y números, en
 * mayúsculas. Así un guion del código del hospital no se cuela en el código
 * (antes "SJ-01" daba "SJ--...") y un tipo vacío usa el respaldo "EQP" en vez
 * de dejar un hueco ("SJ--1234").
 *
 * El sufijo son 6 caracteres aleatorios en base 32 (A-Z y 2-9, sin 0/O ni 1/I
 * para que se lean bien). Usa crypto.getRandomValues cuando existe y Math.random
 * si no. Para pruebas se puede inyectar otro generador de números en [0, 1).
 */

// 32 símbolos: base 36 sin 0, O, 1 e I (los que se confunden al leer).
export const ALFABETO_SUFIJO = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
export const LARGO_SUFIJO = 6

function aleatorioPorDefecto() {
  const cripto = globalThis.crypto
  if (cripto && typeof cripto.getRandomValues === 'function') {
    const valores = new Uint32Array(1)
    cripto.getRandomValues(valores)
    return valores[0] / 2 ** 32
  }
  return Math.random()
}

export function sufijoAleatorio(random = aleatorioPorDefecto, largo = LARGO_SUFIJO) {
  let sufijo = ''
  for (let i = 0; i < largo; i += 1) {
    const indice = Math.min(Math.floor(random() * ALFABETO_SUFIJO.length), ALFABETO_SUFIJO.length - 1)
    sufijo += ALFABETO_SUFIJO[indice]
  }
  return sufijo
}

function parteLimpia(texto, respaldo) {
  const limpio = String(texto ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^A-Za-z0-9]/g, '')
    .slice(0, 3)
    .toUpperCase()
  return limpio || respaldo
}

export function generarCodigoActivo(codigoHospital, tipoActivo, random = aleatorioPorDefecto) {
  const hospital = parteLimpia(codigoHospital, 'XXX')
  const tipo = parteLimpia(tipoActivo, 'EQP')
  return [hospital, tipo, sufijoAleatorio(random)].join('-')
}
