// Logica pura del boton "Sincronizar ahora": textos y tiempos, sin React.

/** "hace 3 min", "hace 2 h"... a partir de la fecha ISO de la ultima sincronizacion. */
export function haceCuanto(lastSyncAt, ahora = Date.now()) {
  if (!lastSyncAt) return null
  const ms = ahora - new Date(lastSyncAt).getTime()
  if (Number.isNaN(ms)) return null
  const min = Math.max(0, Math.floor(ms / 60000))
  if (min < 1) return 'hace un momento'
  if (min < 60) return `hace ${min} min`
  const horas = Math.floor(min / 60)
  if (horas < 24) return `hace ${horas} h`
  const dias = Math.floor(horas / 24)
  return `hace ${dias} ${dias === 1 ? 'dia' : 'dias'}`
}

/** Frase para el title/aria: "Ultima sincronizacion: hace 3 min" o que aun no hubo. */
export function textoUltimaSincronizacion(lastSyncAt, ahora = Date.now()) {
  const cuando = haceCuanto(lastSyncAt, ahora)
  return cuando ? `Última sincronización: ${cuando}` : 'Aún no se ha sincronizado en esta sesión'
}

/** Texto visible del boton segun el estado. */
export function textoBoton({ isOnline, isSyncing }) {
  if (isSyncing) return 'Sincronizando…'
  if (!isOnline) return 'Sin conexión'
  return 'Sincronizar ahora'
}

/** El boton solo se puede tocar con red y sin otra sincronizacion en curso. */
export function botonDeshabilitado({ isOnline, isSyncing }) {
  return !isOnline || isSyncing
}

/** Mensaje breve al terminar. `error` es lastSyncError del store. */
export function mensajeResultado({ error, pendientes = 0 }) {
  if (error) return { tipo: 'error', texto: `No se pudo sincronizar: ${error}` }
  if (pendientes > 0) {
    return {
      tipo: 'aviso',
      texto: `Quedan ${pendientes} ${pendientes === 1 ? 'elemento' : 'elementos'} por enviar`,
    }
  }
  return { tipo: 'ok', texto: 'Todo al día' }
}
