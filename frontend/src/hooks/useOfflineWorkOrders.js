import { useQuery } from '@tanstack/react-query'

import { fetchWorkOrders } from '../api/workOrders'
import {
  getOfflineWorkOrders,
  getWorkOrderIdsWithPendingSync,
  saveWorkOrdersOffline,
} from '../db/repositories'
import useAuthStore from '../store/authStore'
import useNetworkStore from '../store/networkStore'

/**
 * Devuelve las OT del tecnico desde el servidor o desde SQLite segun haya red,
 * con la misma forma en ambos casos para que la pagina no tenga que saberlo.
 *
 * Con conexion tambien vuelca la respuesta a SQLite, que es lo que deja la app
 * lista para trabajar sin red mas tarde.
 *
 * Es deliberadamente UNA sola query con `isOnline` dentro de la clave, en vez
 * de dos alternandose: con dos, el observador de la query inactiva no notificaba
 * al reactivarse y la lista se quedaba vacia justo al perder la conexion.
 */
export function useOfflineWorkOrders(params = {}) {
  const isOnline = useNetworkStore((s) => s.isOnline)
  const user = useAuthStore((s) => s.user)

  const queryResult = useQuery({
    queryKey: ['work-orders', 'offline-aware', isOnline, user?.id ?? null, params],
    queryFn: async () => {
      if (isOnline) {
        const rows = await fetchWorkOrders(params)
        // Cachear para poder servirlas sin red mas adelante.
        try {
          await saveWorkOrdersOffline(rows)
        } catch (error) {
          console.warn('[offline] no se pudieron cachear las OT:', error?.message ?? error)
        }
        return rows
      }

      const rows = await getOfflineWorkOrders(user?.id)
      // El filtro por pestaña lo aplica el servidor cuando hay red; sin red
      // toca hacerlo aqui para que la pagina se comporte igual.
      return params.status ? rows.filter((wo) => wo.status === params.status) : rows
    },
    enabled: !!user?.id,
    // Al cambiar de red cambia la clave: sin esto la lista parpadearia vacia
    // mientras se resuelve la nueva fuente.
    placeholderData: (previous) => previous,
    staleTime: 0,
  })

  return {
    data: queryResult.data ?? [],
    isLoading: queryResult.isLoading,
    error: queryResult.error ?? null,
    refetch: queryResult.refetch,
    isOffline: !isOnline,
  }
}

/**
 * Ids de OT con evidencia o cambios de estado sin subir, para marcar la tarjeta.
 * Se recalcula cuando cambia el estado de sincronizacion.
 */
export function useWorkOrdersWithPendingSync() {
  const pendingSyncCount = useNetworkStore((s) => s.pendingSyncCount)
  const isSyncing = useNetworkStore((s) => s.isSyncing)

  const { data } = useQuery({
    queryKey: ['work-orders', 'pending-sync', pendingSyncCount, isSyncing],
    queryFn: getWorkOrderIdsWithPendingSync,
    staleTime: 0,
  })

  return new Set(data ?? [])
}

export default useOfflineWorkOrders
