import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'

export function useWorkOrderReports(workOrderId) {
  return useQuery({
    queryKey: ['reports', workOrderId],
    queryFn: () =>
      client.get('/api/reports/', { params: { work_order: workOrderId } }).then((r) => r.data),
    enabled: !!workOrderId,
    refetchInterval: (data) => (data && data.length > 0 ? false : 5000),
  })
}

export function useReports(params = {}) {
  return useQuery({
    queryKey: ['reports', params],
    queryFn: () => client.get('/api/reports/', { params }).then((r) => r.data),
  })
}

export function useReportDownload() {
  return useMutation({
    mutationFn: (reportId) =>
      client.get(`/api/reports/${reportId}/download/`).then((r) => r.data),
    onSuccess: (data) => {
      if (data.download_url) {
        window.open(data.download_url, '_blank')
      }
    },
  })
}

export function useResendReportEmail() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (reportId) =>
      client.post(`/api/reports/${reportId}/resend-email/`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}
