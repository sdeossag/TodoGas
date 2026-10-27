/**
 * Con qué layout se muestra "Mi perfil" (/mi-perfil).
 *
 * El técnico tiene su propio menú (TechnicianLayout); el resto de roles que
 * pueden entrar a esa ruta (ADMIN y SUP) usa el de administración (AdminLayout).
 */
export function layoutPerfil(role) {
  return role === 'TEC' ? 'tecnico' : 'administracion'
}
