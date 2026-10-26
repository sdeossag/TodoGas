/**
 * Qué puede hacer un usuario (espejo de backend/apps/users/permisos.py).
 *
 * El servidor manda `permisos` (rol + extras) en el login y en /api/auth/me/, y
 * la app los guarda con el perfil para poder abrirse sin red. Un perfil
 * guardado antes de esta versión no los trae: en ese caso se usan los del rol,
 * que son los mismos que ya tenía, para no quitarle botones a nadie hasta que
 * vuelva a haber conexión.
 */

const SUP = [
  'ot.crear_desde_pendientes', 'ot.asignar', 'ot.revisar', 'tareas.planificar',
  'checklists.gestionar', 'activos.gestionar', 'hallazgos.decidir',
  'inventario.movimientos', 'reportes.ver',
]

const ADMIN = [
  'ot.crear_manual', 'ot.crear_desde_pendientes', 'ot.asignar', 'ot.revisar', 'ot.cancelar',
  'tareas.planificar', 'protocolos.gestionar', 'checklists.gestionar', 'activos.gestionar',
  'contratos.gestionar', 'hallazgos.decidir', 'inventario.articulos', 'inventario.movimientos',
  'reportes.ver',
]

export const PERMISOS_DEL_ROL = { ADMIN, SUP, TEC: [], CLI: [] }

// Con alguno de estos, un técnico ve las órdenes de su alcance y no solo las suyas.
const DE_GESTION_DE_OT = [
  'ot.crear_manual', 'ot.crear_desde_pendientes', 'ot.asignar', 'ot.revisar',
  'ot.cancelar', 'tareas.planificar', 'hallazgos.decidir',
]

export function permisosDe(user) {
  if (!user) return []
  if (Array.isArray(user.permisos)) return user.permisos
  return PERMISOS_DEL_ROL[user.role] ?? []
}

export function puede(user, codigo) {
  return permisosDe(user).includes(codigo)
}

export function puedeAlguno(user, ...codigos) {
  const mios = permisosDe(user)
  return codigos.some((c) => mios.includes(c))
}

/** Entra a las pantallas de gestión: admin, supervisor, o quien tenga algún permiso. */
export function esGestor(user) {
  if (!user || user.role === 'CLI') return false
  return user.role === 'ADMIN' || user.role === 'SUP' || permisosDe(user).length > 0
}

/** Ve la lista de órdenes de trabajo de su alcance. */
export function veOrdenes(user) {
  if (!user || user.role === 'CLI') return false
  return user.role === 'ADMIN' || user.role === 'SUP' || puedeAlguno(user, ...DE_GESTION_DE_OT)
}

/** Edita título, fecha, prioridad... de cualquier orden de su alcance. */
export function editaOrden(user) {
  if (!user || user.role === 'CLI') return false
  return user.role === 'ADMIN' || user.role === 'SUP' || puedeAlguno(user, 'ot.asignar', 'ot.crear_manual')
}

/** Cuántos permisos le sumó el administrador (los de la tabla de usuarios). */
export function cuantosExtra(user) {
  return Array.isArray(user?.permisos_extra) ? user.permisos_extra.length : 0
}

/** Agrupa el catálogo por área, conservando el orden en que llega. */
export function agruparPorArea(catalogo = []) {
  const grupos = []
  for (const p of catalogo) {
    let g = grupos.find((x) => x.area === p.area)
    if (!g) {
      g = { area: p.area, permisos: [] }
      grupos.push(g)
    }
    g.permisos.push(p)
  }
  return grupos
}
