import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'

export function useWorkOrderReports(workOrderId) {
  return useQuery({
    queryKey: ['reports', workOrderId],
    queryFn: () =>
      fetchAllPages(client, '/api/reports/', { work_order: workOrderId }),
    enabled: !!workOrderId,
    // El PDF lo genera Celery despues de completar la OT, asi que hay que
    // sondear. En v5 el callback recibe la Query, no los datos.
    refetchInterval: (query) => {
      const reports = query?.state?.data
      if (Array.isArray(reports) && reports.length > 0) return false
      // Un fallo de Celery no puede dejar la pestaña sondeando indefinidamente.
      if ((query?.state?.dataUpdateCount ?? 0) >= REPORT_POLL_ATTEMPTS) return false
      return 5000
    },
  })
}

/** ~2 minutos de espera antes de rendirse con la generacion del PDF. */
export const REPORT_POLL_ATTEMPTS = 24

export function useReports(params = {}) {
  return useQuery({
    queryKey: ['reports', params],
    queryFn: () => fetchAllPages(client, '/api/reports/', params),
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

/**
 * Relanza la generacion del PDF de una OT completada.
 *
 * El disparador normal es la transicion a COMPLETED; si esa ejecucion fallo,
 * esta es la unica via para recuperar el reporte sin tocar la base de datos.
 */
export function useRegenerateReport(workOrderId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      client.post(`/api/work-orders/${workOrderId}/regenerate-report/`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reports', workOrderId] })
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
