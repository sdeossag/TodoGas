import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'

/**
 * Tareas: cada ocurrencia de una tarea del plan sobre un activo, con su fecha.
 * Las pendientes son lo que el planificador agrupa en OTs.
 */

function invalidateTasks(qc) {
  qc.invalidateQueries({ queryKey: ['tasks'] })
  qc.invalidateQueries({ queryKey: ['maintenance-plans'] })
  qc.invalidateQueries({ queryKey: ['assets'] })
  qc.invalidateQueries({ queryKey: ['assets-page'] })
  qc.invalidateQueries({ queryKey: ['asset-tasks'] })
}

export function useTasks(params = {}, options = {}) {
  return useQuery({
    queryKey: ['tasks', params],
    queryFn: () => fetchAllPages(client, '/api/tasks/', params),
    ...options,
  })
}

export function useTaskReschedules(taskId) {
  return useQuery({
    queryKey: ['tasks', taskId, 'reschedules'],
    queryFn: () => client.get(`/api/tasks/${taskId}/reschedules/`).then((r) => r.data),
    enabled: !!taskId,
  })
}

export function useRescheduleCauses() {
  return useQuery({
    queryKey: ['reschedule-causes'],
    queryFn: () => client.get('/api/reschedule-causes/').then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  })
}

/** Reprograma una o varias pendientes a la misma fecha, con causa. */
export function useRescheduleTasks() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/tasks/reschedule/', data).then((r) => r.data),
    onSuccess: () => invalidateTasks(qc),
  })
}

/** Anula una o varias pendientes con una nota. */
export function useCancelTasks() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/tasks/cancel/', data).then((r) => r.data),
    onSuccess: () => invalidateTasks(qc),
  })
}

/** OT a partir de tareas pendientes, todas del mismo hospital. */
export function useCreateWorkOrderFromTasks() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/work-orders/', data).then((r) => r.data),
    onSuccess: () => {
      invalidateTasks(qc)
      qc.invalidateQueries({ queryKey: ['work-orders'] })
    },
  })
}

/** Próximas fechas e historial de tareas de un activo, con las tres fechas. */
export function useAssetTasks(assetId) {
  return useQuery({
    queryKey: ['asset-tasks', assetId],
    queryFn: () => client.get(`/api/assets/${assetId}/tasks/`).then((r) => r.data),
    enabled: !!assetId,
  })
}
