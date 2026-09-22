import { create } from 'zustand'
import { Network } from '@capacitor/network'

import { countPendingSync } from '../db/repositories'
import { syncOfflineData } from '../sync/syncEngine'

let listenerHandle = null

// Una sincronizacion sin nada en cola termina en milisegundos. Sin un minimo
// visible el banner parpadea y el tecnico no llega a leer que paso.
const MIN_SYNC_VISIBLE_MS = 600

// Cuanto dura en pantalla la confirmacion de una accion guardada sin red.
const OFFLINE_NOTICE_MS = 5000

let noticeTimer = null

// Reintento de lo pendiente mientras hay red. El flanco offline→online no
// basta: con Wi-Fi que no llega al servidor la red nunca "vuelve", y lo que
// quedo en cola de una sesion anterior esperaria al proximo cambio de red.
const RETRY_MS = 60 * 1000
let retryTimer = null

function onVisible() {
  if (document.visibilityState === 'visible') useNetworkStore.getState().syncIfPending()
}

const useNetworkStore = create((set, get) => ({
  isOnline: true,
  isSyncing: false,
  pendingSyncCount: 0,
  lastSyncAt: null,
  lastSyncError: null,
  /** Confirmacion de una accion guardada en el dispositivo. */
  offlineNotice: '',

  /**
   * Arranca la deteccion de conectividad. Idempotente: en desarrollo React
   * monta los efectos dos veces y no queremos dos listeners.
   */
  initNetworkListener: async () => {
    if (listenerHandle) return

    try {
      const status = await Network.getStatus()
      set({ isOnline: status.connected })

      listenerHandle = await Network.addListener('networkStatusChange', (next) => {
        const wasOffline = !get().isOnline
        set({ isOnline: next.connected })

        // Solo sincroniza en el flanco de subida, no en cada evento.
        if (next.connected && wasOffline) {
          get().triggerSync()
        }
      })
    } catch (error) {
      // Sin el plugin (por ejemplo en un navegador antiguo) asumimos online.
      console.warn('[network] no se pudo iniciar la deteccion:', error?.message ?? error)
      set({ isOnline: true })
    }

    await get().refreshPendingCount()

    // Lo que quedo en cola al cerrar la app sin red se sube al abrirla con red.
    get().syncIfPending()
    if (!retryTimer) {
      retryTimer = setInterval(() => get().syncIfPending(), RETRY_MS)
      document.addEventListener('visibilitychange', onVisible)
    }
  },

  /** Sincroniza solo si hay red, algo en cola y ninguna sincronizacion en curso. */
  syncIfPending: () => {
    const { isOnline, isSyncing, pendingSyncCount } = get()
    if (isOnline && !isSyncing && pendingSyncCount > 0) get().triggerSync()
  },

  /**
   * Muestra una confirmacion de ambito app. Va en el store y no en el
   * componente porque la tarjeta que dispara la accion suele desmontarse
   * justo despues (cambia de estado y sale de la pestaña activa).
   */
  showOfflineNotice: (message) => {
    set({ offlineNotice: message })
    if (noticeTimer) clearTimeout(noticeTimer)
    noticeTimer = setTimeout(() => set({ offlineNotice: '' }), OFFLINE_NOTICE_MS)
  },

  removeNetworkListener: async () => {
    if (retryTimer) clearInterval(retryTimer)
    retryTimer = null
    document.removeEventListener('visibilitychange', onVisible)
    if (!listenerHandle) return
    try {
      await listenerHandle.remove()
    } catch {
      // el handle ya puede estar suelto
    }
    listenerHandle = null
  },

  refreshPendingCount: async () => {
    try {
      set({ pendingSyncCount: await countPendingSync() })
    } catch (error) {
      console.warn('[network] no se pudo contar lo pendiente:', error?.message ?? error)
    }
  },

  /** Sube todo lo que quedo guardado sin conexion. Nunca corre dos veces a la vez. */
  triggerSync: async () => {
    if (get().isSyncing) return null
    if (!get().isOnline) return null

    set({ isSyncing: true, lastSyncError: null })
    const startedAt = Date.now()
    try {
      const result = await syncOfflineData({
        onProgress: (pending) => set({ pendingSyncCount: pending }),
      })
      set({ lastSyncAt: new Date().toISOString() })
      return result
    } catch (error) {
      console.error('[network] fallo la sincronizacion:', error)
      set({ lastSyncError: error?.message ?? 'Error de sincronizacion' })
      return null
    } finally {
      const elapsed = Date.now() - startedAt
      if (elapsed < MIN_SYNC_VISIBLE_MS) {
        await new Promise((resolve) => setTimeout(resolve, MIN_SYNC_VISIBLE_MS - elapsed))
      }
      set({ isSyncing: false })
      await get().refreshPendingCount()
    }
  },
}))

export default useNetworkStore
