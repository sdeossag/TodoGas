import { fieldLabel } from '../constants/labels'

const FALLBACK = 'No se pudo completar la acción. Revisa tu conexión e intenta de nuevo.'

/**
 * Mensaje legible de un error de la API (DRF): `detail` si lo hay; si no, cada
 * campo con su nombre en español. Una página de error HTML (500) no se muestra
 * tal cual: el usuario vería el código de la página.
 */
export function apiErrorMessage(err, fallback = FALLBACK) {
  const data = err?.response?.data
  if (!data || typeof data !== 'object') return fallback
  if (data.detail) return String(data.detail)
  const partes = Object.entries(data).map(([campo, valor]) => {
    const texto = Array.isArray(valor) ? valor.join(' ') : String(valor)
    return campo === 'non_field_errors' ? texto : `${fieldLabel(campo)}: ${texto}`
  })
  return partes.join(' · ') || fallback
}
