import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'

const BASE = '/api/maintenance/plans'
const TASKS = '/api/maintenance/plan-tasks'

/**
 * Cualquier cambio en un plan, en sus tareas o en sus activos mueve las tareas
 * pendientes, el calendario y el estado de mantenimiento de los activos.
 */
function invalidatePlanning(qc) {
  qc.invalidateQueries({ queryKey: ['maintenance-plans'] })
  qc.invalidateQueries({ queryKey: ['tasks'] })
  qc.invalidateQueries({ queryKey: ['assets'] })
  qc.invalidateQueries({ queryKey: ['assets-page'] })
}

// ── Planes de tareas ─────────────────────────────────────────────────────────

export function useMaintenancePlans(params = {}) {
  return useQuery({
    queryKey: ['maintenance-plans', params],
    queryFn: () => fetchAllPages(client, `${BASE}/`, params),
  })
}

export function useMaintenancePlan(id) {
  return useQuery({
    queryKey: ['maintenance-plans', id],
    queryFn: () => client.get(`${BASE}/${id}/`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCreateMaintenancePlan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post(`${BASE}/`, data).then((r) => r.data),
    onSuccess: () => invalidatePlanning(qc),
  })
}

export function useUpdateMaintenancePlan(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.patch(`${BASE}/${id}/`, data).then((r) => r.data),
    onSuccess: () => invalidatePlanning(qc),
  })
}

export function usePausePlan(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => client.post(`${BASE}/${id}/pause/`).then((r) => r.data),
    onSuccess: () => invalidatePlanning(qc),
  })
}

export function useResumePlan(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => client.post(`${BASE}/${id}/resume/`).then((r) => r.data),
    onSuccess: () => invalidatePlanning(qc),
  })
}

export function useComplianceData(id) {
  return useQuery({
    queryKey: ['maintenance-plans', id, 'compliance'],
    queryFn: () => client.get(`${BASE}/${id}/compliance/`).then((r) => r.data),
    enabled: !!id,
  })
}

/** Asigna el plan a varios activos; los que tenían otro plan se cambian a este. */
export function useAssignPlanAssets(planId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (assetIds) =>
      client.post(`${BASE}/${planId}/assign-assets/`, { asset_ids: assetIds }).then((r) => r.data),
    onSuccess: () => invalidatePlanning(qc),
  })
}

export function useRemovePlanAssets(planId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (assetIds) =>
      client.post(`${BASE}/${planId}/remove-assets/`, { asset_ids: assetIds }).then((r) => r.data),
    onSuccess: () => invalidatePlanning(qc),
  })
}

// ── Tareas del plan ──────────────────────────────────────────────────────────

export function useSavePlanTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }) =>
      (id ? client.patch(`${TASKS}/${id}/`, data) : client.post(`${TASKS}/`, data)).then((r) => r.data),
    onSuccess: () => invalidatePlanning(qc),
  })
}

export function useDeletePlanTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => client.delete(`${TASKS}/${id}/`),
    onSuccess: () => invalidatePlanning(qc),
  })
}

/** Ocurrencia de una tarea por evento sobre un activo (acta de entrega, prueba anual). */
export function useCreateEventOccurrence() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ planTaskId, asset, scheduled_date }) =>
      client
        .post(`${TASKS}/${planTaskId}/create-occurrence/`, { asset, scheduled_date })
        .then((r) => r.data),
    onSuccess: () => invalidatePlanning(qc),
  })
}
