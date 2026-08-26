import { useMutation, useQuery } from '@tanstack/react-query'
import client from './client'

// El backend cachea la respuesta 300s — usamos el mismo staleTime.
const DASHBOARD_STALE_TIME = 5 * 60 * 1000

export function useDashboard(params = {}) {
  return useQuery({
    queryKey: ['dashboard', params],
    queryFn: () => client.get('/api/dashboard/', { params }).then((r) => r.data),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: false,
  })
}

export function useComplianceHistory(params = {}) {
  return useQuery({
    queryKey: ['dashboard', 'compliance-history', params],
    queryFn: () =>
      client.get('/api/dashboard/compliance-history/', { params }).then((r) => r.data),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: false,
  })
}

export function useAssetsStatus(params = {}) {
  return useQuery({
    queryKey: ['dashboard', 'assets-status', params],
    queryFn: () =>
      client.get('/api/dashboard/assets-status/', { params }).then((r) => r.data),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: false,
  })
}

export function useIntegrityCheck(workOrderId) {
  return useQuery({
    queryKey: ['work-orders', workOrderId, 'integrity'],
    queryFn: () =>
      client.get(`/api/work-orders/${workOrderId}/integrity/`).then((r) => r.data),
    enabled: !!workOrderId,
    retry: false,
  })
}

export function useGenerateConsolidatedReport() {
  return useMutation({
    mutationFn: ({ hospital_id, date_from, date_to, task_type }) =>
      client
        .post('/api/reports/consolidated/', {
          hospital_id: hospital_id || null,
          date_from,
          date_to,
          task_type: task_type || null,
        })
        .then((r) => r.data),
  })
}
