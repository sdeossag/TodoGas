import { create } from 'zustand'
import { Preferences } from '@capacitor/preferences'
import client from '../api/client'

const CACHED_USER_KEY = 'cached_user'

/**
 * Guarda el perfil para poder abrir la app sin red. En navegador Preferences
 * usa localStorage por debajo; en Android, SharedPreferences.
 */
async function cacheUser(user) {
  try {
    await Preferences.set({ key: CACHED_USER_KEY, value: JSON.stringify(user) })
  } catch (error) {
    console.warn('[auth] no se pudo cachear el usuario:', error?.message ?? error)
  }
}

async function readCachedUser() {
  try {
    const { value } = await Preferences.get({ key: CACHED_USER_KEY })
    return value ? JSON.parse(value) : null
  } catch (error) {
    console.warn('[auth] no se pudo leer el usuario cacheado:', error?.message ?? error)
    return null
  }
}

async function clearCachedUser() {
  try {
    await Preferences.remove({ key: CACHED_USER_KEY })
  } catch {
    // si no estaba, no hay nada que limpiar
  }
}

const useAuthStore = create((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  /** true cuando la sesion se restauro de cache por falta de red. */
  isSessionFromCache: false,

  login: async (email, password) => {
    const { data } = await client.post('/api/auth/login/', { email, password })
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    await cacheUser(data.user)
    set({ user: data.user, isAuthenticated: true, isSessionFromCache: false })
    return data.user
  },

  logout: async () => {
    const refresh = localStorage.getItem('refresh_token')
    try {
      if (refresh) {
        await client.post('/api/auth/logout/', { refresh })
      }
    } catch {
      // Ignorar errores en logout — el token puede ya estar vencido
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      await clearCachedUser()
      set({ user: null, isAuthenticated: false, isSessionFromCache: false })
    }
  },

  /**
   * Restaura la sesion al arrancar.
   *
   * Distingue rechazo de credenciales de fallo de red: un 401 cierra sesion,
   * pero quedarse sin cobertura no puede expulsar al tecnico. En ese caso los
   * tokens se conservan (siguen siendo validos) y el perfil sale de cache.
   */
  loadUser: async () => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      set({ isLoading: false })
      return
    }

    try {
      const { data } = await client.get('/api/auth/me/')
      await cacheUser(data)
      set({ user: data, isAuthenticated: true, isLoading: false, isSessionFromCache: false })
      return
    } catch (error) {
      const status = error?.response?.status

      // Solo el servidor puede invalidar la sesion.
      if (status === 401 || status === 403) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        await clearCachedUser()
        set({ user: null, isAuthenticated: false, isLoading: false, isSessionFromCache: false })
        return
      }

      // Sin respuesta del servidor: es un problema de red, no de credenciales.
      const cached = await readCachedUser()
      if (cached) {
        set({
          user: cached,
          isAuthenticated: true,
          isLoading: false,
          isSessionFromCache: true,
        })
        return
      }

      // Nunca se cargo el perfil en este dispositivo: no hay nada que restaurar.
      // Los tokens se conservan a proposito, siguen siendo validos.
      set({ user: null, isAuthenticated: false, isLoading: false, isSessionFromCache: false })
    }
  },

  changePassword: async (currentPassword, newPassword, newPasswordConfirm) => {
    await client.post('/api/auth/change-password/', {
      current_password: currentPassword,
      new_password: newPassword,
      new_password_confirm: newPasswordConfirm,
    })
    // Recargar usuario para limpiar el flag must_change_password
    const { data } = await client.get('/api/auth/me/')
    await cacheUser(data)
    set({ user: data })
  },
}))

export default useAuthStore
