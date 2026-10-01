/**
 * Quién puede quedar asignado a una OT y ejecutarla (decisión del 2026-10-01).
 * Además del técnico, el administrador y el supervisor: hacen reportes de
 * instalaciones a las que no va un técnico de mantenimiento.
 */
export const ROLES_EJECUTORES = ['TEC', 'ADMIN', 'SUP']

const ROL = { ADMIN: 'Administrador', SUP: 'Supervisor' }

/** Los usuarios activos que pueden ejecutar: primero los técnicos, luego por nombre. */
export function ejecutores(users = []) {
  return users
    .filter((u) => u.is_active && ROLES_EJECUTORES.includes(u.role))
    .sort((a, b) =>
      (a.role === 'TEC' ? 0 : 1) - (b.role === 'TEC' ? 0 : 1)
      || nombre(a).localeCompare(nombre(b), 'es'))
}

function nombre(u) {
  return `${u.first_name ?? ''} ${u.last_name ?? ''}`.trim() || u.email
}

/** "Ana Ruiz" para un técnico; "Luis Gómez (Supervisor)" para los demás. */
export function etiquetaEjecutor(u) {
  return ROL[u.role] ? `${nombre(u)} (${ROL[u.role]})` : nombre(u)
}

/** La OT está asignada a este usuario y su rol puede ejecutarla. */
export function laEjecuto(user, wo) {
  return !!user && ROLES_EJECUTORES.includes(user.role) && wo?.assigned_to?.id === user.id
}
