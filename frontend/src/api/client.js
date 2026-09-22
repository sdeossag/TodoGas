import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Agrega el access token a cada request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error)
    else prom.resolve(token)
  })
  failedQueue = []
}

// Intenta renovar el token cuando recibe 401
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return client(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      const refresh = localStorage.getItem('refresh_token')
      if (!refresh) {
        clearAuthAndRedirect()
        return Promise.reject(error)
      }

      try {
        const { data } = await axios.post(`${BASE_URL}/api/auth/refresh/`, {
          refresh,
        })
        localStorage.setItem('access_token', data.access)
        client.defaults.headers.common.Authorization = `Bearer ${data.access}`
        processQueue(null, data.access)
        originalRequest.headers.Authorization = `Bearer ${data.access}`
        return client(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        // Solo cerramos sesion si el servidor rechazo el refresh. Si la
        // peticion ni siquiera llego, es falta de red: los tokens siguen
        // siendo validos y expulsar al tecnico seria un error.
        if (refreshError.response) clearAuthAndRedirect()
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

/**
 * Marca por que se cerro la sesion para que LoginPage lo cuente.
 *
 * Va en sessionStorage, no en el estado de React: la redireccion es un
 * `location.href`, asi que la app se remonta entera y cualquier estado en
 * memoria se pierde por el camino.
 */
export const SESSION_EXPIRED_KEY = 'todogas.session_expired'

/**
 * URL de un archivo de media (foto, firma, acta). Con almacenamiento local el
 * backend la devuelve relativa (/media/...): en la web la resuelve el proxy de
 * Vite, pero en la app Android apuntaria a la propia app (https://localhost).
 * Las de S3 ya vienen absolutas y pasan tal cual.
 */
export function mediaUrl(url) {
  return url?.startsWith('/') ? `${BASE_URL}${url}` : url
}

function clearAuthAndRedirect() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  try {
    sessionStorage.setItem(SESSION_EXPIRED_KEY, '1')
  } catch {
    // Modo privado sin sessionStorage: se pierde el aviso, no la redireccion.
  }
  // Ya estamos en /login (por ejemplo, credenciales rechazadas): recargar
  // borraria el error que el formulario acaba de mostrar.
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

export default client
