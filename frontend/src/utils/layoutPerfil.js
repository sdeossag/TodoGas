/**
 * Con qué layout se muestra "Mi perfil" (/mi-perfil).
 *
 * El técnico tiene su propio menú (TechnicianLayout); la cuenta de hospital
 * (CLI) usa el suyo (ClientLayout); el resto de roles que pueden entrar a esa
 * ruta (ADMIN y SUP) usa el de administración (AdminLayout).
 */
export function layoutPerfil(role) {
  if (role === 'TEC') return 'tecnico'
  if (role === 'CLI') return 'cliente'
  return 'administracion'
}
