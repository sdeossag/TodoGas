// Decide si la app se bloquea con el aviso de privacidad (Ley 1581 de 2012).
// Logica pura, sin red ni React, para poder probarla con node --test.

export const claveLocal = (userId) => `todogas.privacidad.${userId}`

/**
 * - 'permitir': se usa la app.
 * - 'pedir': pantalla bloqueante con el aviso.
 * - 'esperar': aun sin respuesta del servidor y sin constancia local.
 *
 * Sin respuesta del servidor (sin red, caida, error) no se bloquea: quien
 * inicia sesion ya tuvo red y vio el aviso, y dejar sin app a un tecnico en un
 * sotano sin senal es peor que posponer la pregunta a la siguiente conexion.
 */
export function estadoDelAviso({ cargando, error, datos, aceptadaLocal, versionApp }) {
  if (datos) return datos.required ? 'pedir' : 'permitir'
  if (error) return 'permitir'
  if (cargando) return aceptadaLocal && aceptadaLocal === versionApp ? 'permitir' : 'esperar'
  return 'permitir'
}

export function leerAceptadaLocal(userId, storage = globalThis.localStorage) {
  try {
    return storage?.getItem(claveLocal(userId)) || null
  } catch {
    return null
  }
}

export function guardarAceptadaLocal(userId, version, storage = globalThis.localStorage) {
  try {
    storage?.setItem(claveLocal(userId), version)
  } catch {
    // sin almacenamiento solo se vuelve a consultar al servidor
  }
}

/** Nombre del archivo de "Descargar mis datos". */
export function nombreArchivoDatos(fecha = new Date()) {
  return `mis-datos-personales-${fecha.toISOString().slice(0, 10)}.json`
}

/** Linea bajo la firma de quien recibe en el hospital (sigue el enlace al aviso). */
export const TEXTO_AUTORIZACION_FIRMA =
  'Al firmar autoriza el tratamiento de su nombre, cargo y firma para el acta de servicio, según el aviso de privacidad de'

export const TEXTO_RECORDATORIO_USUARIOS =
  'Antes de crear la cuenta, asegúrate de tener la autorización del titular para tratar sus datos personales (Ley 1581 de 2012).'
