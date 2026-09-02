import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'

export function useInventoryItems(filters = {}) {
  return useQuery({
    queryKey: ['inventory-items', filters],
    queryFn: () => fetchAllPages(client, '/api/inventory/items/', filters),
  })
}

export function useInventoryItem(id) {
  return useQuery({
    queryKey: ['inventory-items', id],
    queryFn: () => client.get(`/api/inventory/items/${id}/`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCreateInventoryItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/inventory/items/', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory-items'] }),
  })
}

export function useUpdateInventoryItem(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.patch(`/api/inventory/items/${id}/`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory-items', id] })
      qc.invalidateQueries({ queryKey: ['inventory-items'] })
    },
  })
}

export function useLowStockItems() {
  return useQuery({
    queryKey: ['inventory-items-low-stock'],
    queryFn: () => client.get('/api/inventory/items/low-stock/').then((r) => r.data),
  })
}

export function useStockMovements(filters = {}) {
  return useQuery({
    queryKey: ['stock-movements', filters],
    queryFn: () => fetchAllPages(client, '/api/inventory/movements/', filters),
    enabled: Object.values(filters).some(Boolean) || Object.keys(filters).length === 0,
  })
}

export function useCreateStockMovement() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/inventory/movements/', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory-items'] })
      qc.invalidateQueries({ queryKey: ['inventory-items-low-stock'] })
      qc.invalidateQueries({ queryKey: ['stock-movements'] })
      qc.invalidateQueries({ queryKey: ['inventory-alerts'] })
    },
  })
}

export function useStockAlerts() {
  return useQuery({
    queryKey: ['inventory-alerts'],
    queryFn: () => client.get('/api/inventory/alerts/').then((r) => r.data),
    staleTime: 60000,
    refetchInterval: 60000,
    retry: false,
  })
}
