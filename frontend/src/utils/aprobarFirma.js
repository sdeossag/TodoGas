/**
 * Logica pura del dialogo de aprobacion de una OT (sin React).
 * Al aprobar, el servidor firma con la firma guardada de quien aprueba; si no
 * tiene una, responde 400 con code "firma_requerida".
 */

export const CODIGO_FIRMA_REQUERIDA = 'firma_requerida'

const DETALLE_FIRMA_DEFECTO = 'Registra tu firma en Mi perfil para aprobar esta orden.'

/** true si el error de la transicion es la falta de firma guardada. */
export function esErrorFirmaRequerida(err) {
  return err?.response?.data?.code === CODIGO_FIRMA_REQUERIDA
}

/** El texto que manda el servidor, o el de por defecto si no llega ninguno. */
export function mensajeFirmaRequerida(err) {
  const detalle = err?.response?.data?.detail
  return typeof detalle === 'string' && detalle.trim() ? detalle.trim() : DETALLE_FIRMA_DEFECTO
}

/**
 * Que mostrar en el dialogo de aprobar.
 *   cargando: la firma guardada todavia se esta consultando
 *   dataUrl:  la firma guardada (data URL) o null si no hay
 */
export function estadoDialogoAprobar({ cargando, dataUrl }) {
  if (cargando) {
    return { tipo: 'cargando', puedeAprobar: false, texto: 'Cargando tu firma...' }
  }
  if (dataUrl) {
    return {
      tipo: 'con_firma',
      puedeAprobar: true,
      texto: 'Se firmará con tu firma guardada',
      textoBoton: 'Aprobar y firmar',
    }
  }
  return {
    tipo: 'sin_firma',
    puedeAprobar: false,
    texto: 'Para aprobar necesitas registrar tu firma',
    textoEnlace: 'Ir a Mi perfil para registrarla',
  }
}
