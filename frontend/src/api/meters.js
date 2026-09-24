import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'

/** Unidades de medidor (HORAS, PSI…). `active: true` para los formularios. */
export function useMeterUnits({ active = false } = {}) {
  return useQuery({
    queryKey: ['meter-units', { active }],
    queryFn: () => client.get('/api/meter-units/', { params: active ? { active: 1 } : {} }).then((r) => r.data),
    staleTime: 10 * 60_000,
  })
}

/** Medidores de un equipo con su última lectura y cómo van sus activadores. */
export function useMeters(assetId) {
  return useQuery({
    queryKey: ['meters', assetId],
    queryFn: () => client.get('/api/meters/', { params: { asset_id: assetId } }).then((r) => r.data),
    enabled: !!assetId,
  })
}

export function useMeterReadings(meterId, options = {}) {
  return useQuery({
    queryKey: ['meter-readings', meterId],
    queryFn: () => fetchAllPages(client, '/api/meter-readings/', { meter_id: meterId }),
    enabled: !!meterId,
    ...options,
  })
}

function invalidar(qc) {
  qc.invalidateQueries({ queryKey: ['meters'] })
  qc.invalidateQueries({ queryKey: ['meter-readings'] })
  // Una lectura puede abrir una tarea pendiente.
  qc.invalidateQueries({ queryKey: ['tasks'] })
}

export function useCreateMeter() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/meters/', data).then((r) => r.data),
    onSuccess: () => invalidar(qc),
  })
}

export function useCreateReading() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/meter-readings/', data).then((r) => r.data),
    onSuccess: () => invalidar(qc),
  })
}

export function useDeleteReading() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => client.delete(`/api/meter-readings/${id}/`),
    onSuccess: () => invalidar(qc),
  })
}

export const COMPARATORS = [
  { value: 'LT', label: 'Menor que' },
  { value: 'LTE', label: 'Menor o igual a' },
  { value: 'GT', label: 'Mayor que' },
  { value: 'GTE', label: 'Mayor o igual a' },
  { value: 'EQ', label: 'Igual a' },
  { value: 'NE', label: 'Diferente a' },
]

/** 12500 → "12.500"; 13.5 → "13,5". */
export function formatReading(n) {
  if (n === null || n === undefined) return '—'
  return Number(n).toLocaleString('es-CO', { maximumFractionDigits: 3 })
}
