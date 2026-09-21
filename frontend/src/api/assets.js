import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages, unwrapPage } from './pagination'

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

export function useAssetTree(hospitalId, options = {}) {
  return useQuery({
    queryKey: ['asset-tree', hospitalId],
    queryFn: () =>
      client.get('/api/asset-nodes/tree/', { params: { hospital_id: hospitalId } }).then((r) => r.data),
    enabled: !!hospitalId,
    ...options,
  })
}

/**
 * Todas las ubicaciones de un hospital en lista plana, activas e inactivas,
 * con `children_count` y `asset_count`. Es lo que usa el editor de ubicaciones;
 * /tree/ no sirve ahí porque oculta las inactivas y no trae conteos.
 */
export function useAssetNodes(hospitalId) {
  return useQuery({
    queryKey: ['asset-nodes', hospitalId],
    queryFn: () => fetchAllPages(client, '/api/asset-nodes/', { hospital_id: hospitalId }),
    enabled: !!hospitalId,
  })
}

// Cualquier cambio en una ubicación toca las dos vistas del árbol: el editor
// (lista plana) y los selectores de ubicación de los formularios (/tree/).
function invalidateNodes(qc) {
  qc.invalidateQueries({ queryKey: ['asset-nodes'] })
  qc.invalidateQueries({ queryKey: ['asset-tree'] })
}

export function useCreateAssetNode() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/asset-nodes/', data).then((r) => r.data),
    onSuccess: () => invalidateNodes(qc),
  })
}

export function useUpdateAssetNode() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }) =>
      client.patch(`/api/asset-nodes/${id}/`, data).then((r) => r.data),
    onSuccess: () => {
      invalidateNodes(qc)
      // Mover o renombrar cambia el `path` que muestran los activos.
      qc.invalidateQueries({ queryKey: ['assets'] })
      qc.invalidateQueries({ queryKey: ['assets-page'] })
    },
  })
}

export function useDeleteAssetNode() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => client.delete(`/api/asset-nodes/${id}/`),
    onSuccess: () => invalidateNodes(qc),
  })
}

// ── Assets ─────────────────────────────────────────────────────────────────

export function useAssets(params = {}) {
  return useQuery({
    queryKey: ['assets', params],
    queryFn: () => fetchAllPages(client, '/api/assets/', params),
  })
}

/**
 * Una sola página de activos, para la vista principal con paginador real.
 *
 * A diferencia de useAssets (que recorre todo para los desplegables), este
 * respeta la paginación del servidor: pide `page` y devuelve
 * { items, count, hasNext, hasPrev }. keepPreviousData evita el parpadeo a
 * vacío al cambiar de página.
 */
export function useAssetsPage(params = {}) {
  return useQuery({
    queryKey: ['assets-page', params],
    queryFn: () =>
      client.get('/api/assets/', { params }).then((r) => unwrapPage(r.data)),
    placeholderData: keepPreviousData,
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
      qc.invalidateQueries({ queryKey: ['asset-nodes'] })
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
      qc.invalidateQueries({ queryKey: ['asset-nodes'] })
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
