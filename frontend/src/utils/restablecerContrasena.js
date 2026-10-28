const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** Errores por campo de la pantalla «¿Olvidaste tu contraseña?». Vacío si todo está bien. */
export function validarCorreo(email) {
  const valor = (email ?? '').trim()
  if (!valor) return { email: 'Ingresa tu correo electrónico.' }
  if (!EMAIL_RE.test(valor)) return { email: 'El formato del correo no es válido.' }
  return {}
}

/** Errores por campo de la pantalla de contraseña nueva. Vacío si todo está bien. */
export function validarNuevaContrasena(nueva, confirmacion) {
  const errs = {}
  if (!nueva || nueva.length < 8) errs.next = 'Mínimo 8 caracteres.'
  if (nueva !== confirmacion) errs.confirm = 'Las contraseñas no coinciden.'
  return errs
}
