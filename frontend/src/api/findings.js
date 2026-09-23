import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'

/**
 * Hallazgos (bloque E): lo que el técnico encuentra en un equipo durante la
 * visita. `params`: work_order, asset, status (PENDING = bandeja), severity.
 */
export function useFindings(params = {}, options = {}) {
  return useQuery({
    queryKey: ['findings', params],
    queryFn: () => fetchAllPages(client, '/api/findings/', params),
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

export function useCreateFinding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/findings/', data).then((r) => r.data),
    onSuccess: () => invalidar(qc),
  })
}

export function useUpdateFinding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }) => client.patch(`/api/findings/${id}/`, data).then((r) => r.data),
    onSuccess: () => invalidar(qc),
  })
}

export function useDeleteFinding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => client.delete(`/api/findings/${id}/`),
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
