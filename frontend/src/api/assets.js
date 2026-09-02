import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'

// ── Hospitals ──────────────────────────────────────────────────────────────

export function useHospitals(params = {}) {
  return useQuery({
    queryKey: ['hospitals', params],
    queryFn: () => fetchAllPages(client, '/api/hospitals/', params),
  })
}

export function useHospital(id) {
  return useQuery({
    queryKey: ['hospitals', id],
    queryFn: () => client.get(`/api/hospitals/${id}/`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCreateHospital() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/hospitals/', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hospitals'] }),
  })
}

export function useUpdateHospital(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.patch(`/api/hospitals/${id}/`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hospitals', id] })
      qc.invalidateQueries({ queryKey: ['hospitals'] })
    },
  })
}

export function useToggleHospitalActive(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => client.post(`/api/hospitals/${id}/toggle-active/`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hospitals'] }),
  })
}

// ── Asset nodes / tree ─────────────────────────────────────────────────────

export function useAssetTree(hospitalId) {
  return useQuery({
    queryKey: ['asset-tree', hospitalId],
    queryFn: () =>
      client.get('/api/asset-nodes/tree/', { params: { hospital_id: hospitalId } }).then((r) => r.data),
    enabled: !!hospitalId,
  })
}

// ── Assets ─────────────────────────────────────────────────────────────────

export function useAssets(params = {}) {
  return useQuery({
    queryKey: ['assets', params],
    queryFn: () => fetchAllPages(client, '/api/assets/', params),
  })
}

export function useAsset(id) {
  return useQuery({
    queryKey: ['assets', id],
    queryFn: () => client.get(`/api/assets/${id}/`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCreateAsset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/assets/', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] })
      qc.invalidateQueries({ queryKey: ['asset-tree'] })
    },
  })
}

export function useUpdateAsset(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.patch(`/api/assets/${id}/`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets', id] })
      qc.invalidateQueries({ queryKey: ['assets'] })
      qc.invalidateQueries({ queryKey: ['asset-tree'] })
    },
  })
}

export function useDecommissionAsset(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => client.post(`/api/assets/${id}/decommission/`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets', id] })
      qc.invalidateQueries({ queryKey: ['assets'] })
    },
  })
}
