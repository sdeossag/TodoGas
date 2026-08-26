import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'

/** Fetcher suelto: lo comparten useWorkOrders y el hook offline. */
export function fetchWorkOrders(params = {}) {
  return client.get('/api/work-orders/', { params }).then((r) => r.data)
}

export function useWorkOrders(params = {}, options = {}) {
  return useQuery({
    queryKey: ['work-orders', params],
    queryFn: () => fetchWorkOrders(params),
    ...options,
  })
}

export function useWorkOrder(id) {
  return useQuery({
    queryKey: ['work-orders', id],
    queryFn: () => client.get(`/api/work-orders/${id}/`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCreateWorkOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/work-orders/', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['work-orders'] }),
  })
}

export function useUpdateWorkOrder(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.patch(`/api/work-orders/${id}/`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-orders', id] })
      qc.invalidateQueries({ queryKey: ['work-orders'] })
    },
  })
}

export function useTransitionWorkOrder(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ new_status, comment = '' }) =>
      client.post(`/api/work-orders/${id}/transition/`, { new_status, comment }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-orders', id] })
      qc.invalidateQueries({ queryKey: ['work-orders'] })
    },
  })
}

export function useAssignWorkOrder(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ assigned_to }) =>
      client.post(`/api/work-orders/${id}/assign/`, { assigned_to }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['work-orders', id] }),
  })
}

export function useCancelWorkOrder(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ comment }) =>
      client.post(`/api/work-orders/${id}/cancel/`, { comment }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-orders', id] })
      qc.invalidateQueries({ queryKey: ['work-orders'] })
    },
  })
}

export function useWorkOrderHistory(id, allowed = true) {
  return useQuery({
    queryKey: ['work-orders', id, 'history'],
    queryFn: () => client.get(`/api/work-orders/${id}/history/`).then((r) => r.data),
    enabled: !!id && allowed,
  })
}
