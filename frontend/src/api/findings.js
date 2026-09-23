import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'
import {
  deleteFindingOffline,
  getOfflineFindings,
  newId,
  saveFindingOffline,
  saveFindingsFromServer,
} from '../db/repositories'
import useAuthStore from '../store/authStore'
import useNetworkStore from '../store/networkStore'

/**
 * Hallazgos (bloque E): lo que el técnico encuentra en un equipo durante la
 * visita. `params`: work_order, asset, status (PENDING = bandeja), severity.
 */
export function useFindings(params = {}, options = {}) {
  const isOnline = useNetworkStore((s) => s.isOnline)
  const role = useAuthStore((s) => s.user?.role)
  // Los de una OT del técnico se guardan en el teléfono: sin red los ve y los
  // corrige (bloque E, corte C).
  const deSuOT = role === 'TEC' && !!params.work_order
  return useQuery({
    queryKey: ['findings', params, isOnline ? 'online' : 'offline'],
    queryFn: async () => {
      if (!isOnline && deSuOT) return getOfflineFindings(params.work_order)
      const datos = await fetchAllPages(client, '/api/findings/', params)
      if (!deSuOT) return datos
      await saveFindingsFromServer(params.work_order, datos)
      // Con lo que haya en cola encima (lo hecho sin red que aún no sube).
      const locales = await getOfflineFindings(params.work_order)
      return locales.length ? locales : datos
    },
    placeholderData: (previous) => previous,
    // Sin red lee SQLite: que TanStack no la pause por navigator.onLine.
    networkMode: 'always',
    ...options,
  })
}

/** Pendientes de la bandeja, por severidad: para el menú y el tablero. */
export function useFindingsSummary(options = {}) {
  return useQuery({
    queryKey: ['findings', 'summary'],
    queryFn: () => client.get('/api/findings/summary/').then((r) => r.data),
    refetchInterval: 60_000,
    ...options,
  })
}

function invalidar(qc) {
  qc.invalidateQueries({ queryKey: ['findings'] })
}

/** Sin red: queda en el teléfono y avisa, como las fotos y el checklist. */
function useSinRed() {
  const isOnline = useNetworkStore((s) => s.isOnline)
  const refreshPendingCount = useNetworkStore((s) => s.refreshPendingCount)
  const showOfflineNotice = useNetworkStore((s) => s.showOfflineNotice)
  return {
    isOnline,
    async enCola(mensaje) {
      await refreshPendingCount()
      showOfflineNotice(mensaje)
    },
  }
}

/**
 * `data` con la forma de la API más `asset_info` (el formulario la conoce):
 * sin red es lo que se muestra hasta sincronizar. El id lo pone el teléfono
 * siempre, con o sin red.
 */
export function useCreateFinding() {
  const qc = useQueryClient()
  const { isOnline, enCola } = useSinRed()
  return useMutation({
    mutationFn: async ({ asset_info, ...data }) => {
      const conId = { id: newId(), ...data }
      if (!isOnline) {
        const reporter = useAuthStore.getState().user
        const local = await saveFindingOffline({
          ...conId,
          asset_info,
          reported_by_name: `${reporter?.first_name ?? ''} ${reporter?.last_name ?? ''}`.trim(),
          photos_count: 0,
        })
        await enCola('Hallazgo guardado. Se sincronizará al reconectar.')
        return local
      }
      return client.post('/api/findings/', conId).then((r) => r.data)
    },
    // Sin red guarda en SQLite: TanStack pausaria la mutacion y quedaria
    // "Guardando..." para siempre.
    networkMode: 'always',
    onSuccess: () => invalidar(qc),
  })
}

export function useUpdateFinding() {
  const qc = useQueryClient()
  const { isOnline, enCola } = useSinRed()
  return useMutation({
    mutationFn: async ({ id, ...data }) => {
      if (!isOnline) {
        const local = await saveFindingOffline({ id, ...data })
        await enCola('Cambio guardado. Se sincronizará al reconectar.')
        return local
      }
      return client.patch(`/api/findings/${id}/`, data).then((r) => r.data)
    },
    // Sin red guarda en SQLite: TanStack pausaria la mutacion y quedaria
    // "Guardando..." para siempre.
    networkMode: 'always',
    onSuccess: () => invalidar(qc),
  })
}

export function useDeleteFinding() {
  const qc = useQueryClient()
  const { isOnline, enCola } = useSinRed()
  return useMutation({
    mutationFn: async (id) => {
      if (!isOnline) {
        await deleteFindingOffline(id)
        await enCola('Hallazgo quitado. Se sincronizará al reconectar.')
        return
      }
      await client.delete(`/api/findings/${id}/`)
    },
    // Sin red guarda en SQLite: TanStack pausaria la mutacion y quedaria
    // "Guardando..." para siempre.
    networkMode: 'always',
    onSuccess: () => invalidar(qc),
  })
}

export function useConvertFinding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, scheduled_date, note }) =>
      client.post(`/api/findings/${id}/convert/`, { scheduled_date, note }).then((r) => r.data),
    onSuccess: () => {
      invalidar(qc)
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

export function useDismissFinding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, note }) =>
      client.post(`/api/findings/${id}/dismiss/`, { note }).then((r) => r.data),
    onSuccess: () => invalidar(qc),
  })
}

export const SEVERITIES = [
  { value: 'LOW', label: 'Baja' },
  { value: 'MEDIUM', label: 'Media' },
  { value: 'HIGH', label: 'Alta' },
  { value: 'CRITICAL', label: 'Crítica' },
]

export const SEVERITY_COLORS = {
  LOW: 'bg-gray-100 text-gray-700',
  MEDIUM: 'bg-amber-50 text-amber-700',
  HIGH: 'bg-orange-100 text-orange-800',
  CRITICAL: 'bg-red-100 text-red-800',
}

export const FINDING_STATUS_COLORS = {
  RESOLVED: 'bg-green-50 text-green-700',
  PENDING: 'bg-amber-50 text-amber-700',
  CONVERTED: 'bg-blue-50 text-blue-700',
  DISMISSED: 'bg-gray-100 text-gray-600',
}
