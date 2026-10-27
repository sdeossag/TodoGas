/**
 * Logica pura de la firma guardada del usuario (sin React ni base de datos):
 * quien puede tenerla, y que firma se usa segun haya red o no.
 */

const SOLO_ROLES_DEL_SISTEMA = ['TEC', 'SUP', 'ADMIN']

/** Las cuentas de hospital (CLI) no guardan firma: la de quien recibe se dibuja siempre. */
export function puedeTenerFirmaGuardada(role) {
  return SOLO_ROLES_DEL_SISTEMA.includes(role)
}

/** Imagen PNG de una data URL, sin el prefijo; vacio si no hay. */
export function base64DeDataUrl(dataUrl) {
  if (!dataUrl) return ''
  return String(dataUrl).replace(/^data:image\/\w+;base64,/, '')
}

/**
 * La firma que se ofrece al firmar una OT. Con red manda el servidor (si dice
 * que no hay firma, no se ofrece la copia local aunque exista: la borraron en
 * otro lado). Sin red, o si el servidor no respondio, vale la copia del telefono.
 *
 *   remota: respuesta de GET /api/evidence/my-signature/ o null si no hubo respuesta
 *   local:  data URL guardada en el telefono o null
 *
 * Devuelve { dataUrl, origen } con origen 'servidor' | 'telefono' | null.
 */
export function elegirFirmaGuardada({ remota, local }) {
  if (remota) {
    if (remota.exists && remota.image_data) return { dataUrl: remota.image_data, origen: 'servidor' }
    return { dataUrl: null, origen: null }
  }
  if (local) return { dataUrl: local, origen: 'telefono' }
  return { dataUrl: null, origen: null }
}

/** Cargo con el que sale en el acta cuando se firma con la firma guardada. */
export function cargoDelFirmante(role) {
  return { TEC: 'Técnico', SUP: 'Supervisor', ADMIN: 'Administrador' }[role] ?? ''
}
