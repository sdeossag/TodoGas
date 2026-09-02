import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'

const BASE = '/api/maintenance/plans'

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
    onSuccess: () => qc.invalidateQueries({ queryKey: ['maintenance-plans'] }),
  })
}

export function useUpdateMaintenancePlan(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.patch(`${BASE}/${id}/`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['maintenance-plans', id] })
      qc.invalidateQueries({ queryKey: ['maintenance-plans'] })
    },
  })
}

export function useTriggerPlan(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => client.post(`${BASE}/${id}/trigger/`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['maintenance-plans'] })
      qc.invalidateQueries({ queryKey: ['work-orders'] })
    },
  })
}

export function usePausePlan(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => client.post(`${BASE}/${id}/pause/`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['maintenance-plans', id] }),
  })
}

export function useResumePlan(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => client.post(`${BASE}/${id}/resume/`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['maintenance-plans', id] }),
  })
}

export function useComplianceData(id) {
  return useQuery({
    queryKey: ['maintenance-plans', id, 'compliance'],
    queryFn: () => client.get(`${BASE}/${id}/compliance/`).then((r) => r.data),
    enabled: !!id,
  })
}
