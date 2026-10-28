import client from './client'

/** Pide el enlace para restablecer la contraseña. Responde igual exista o no el correo. */
export function requestPasswordReset(email) {
  return client.post('/api/auth/password-reset/', { email }).then((r) => r.data)
}

/** Fija la contraseña nueva con el uid y el token del enlace del correo. */
export function confirmPasswordReset({ uid, token, newPassword }) {
  return client
    .post('/api/auth/password-reset/confirm/', {
      uid,
      token,
      new_password: newPassword,
    })
    .then((r) => r.data)
}
