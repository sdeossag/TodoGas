import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'

/**
 * Contratos de mantenimiento y garantías de equipos (Gestión Documental de
 * Fracttal). `params`: hospital_id, kind, status, asset_id, search.
 */
export function useContracts(params = {}, options = {}) {
  return useQuery({
    queryKey: ['contracts', params],
    queryFn: () => fetchAllPages(client, '/api/contracts/', params),
    ...options,
  })
}

/** Lo que vence pronto y los hospitales sin contrato vigente: para el tablero. */
export function useContractsSummary(options = {}) {
  return useQuery({
    queryKey: ['contracts', 'summary'],
    queryFn: () => client.get('/api/contracts/summary/').then((r) => r.data),
    ...options,
  })
}

/**
 * Con archivo va como multipart; sin él, como JSON. `asset_ids` se repite
 * en el multipart, que es como DRF lee una lista.
 */
function cuerpo(data) {
  if (!(data.file instanceof File)) {
    const { file: _sinArchivo, ...resto } = data
    return resto
  }
  const fd = new FormData()
  for (const [k, v] of Object.entries(data)) {
    if (v === undefined) continue
    if (Array.isArray(v)) v.forEach((x) => fd.append(k, x))
    else fd.append(k, v === null ? '' : v)
  }
  return fd
}

function invalidar(qc) {
  qc.invalidateQueries({ queryKey: ['contracts'] })
  // El estado de contrato vive también en la lista de hospitales y en la ficha del equipo.
  qc.invalidateQueries({ queryKey: ['hospitals'] })
  qc.invalidateQueries({ queryKey: ['assets'] })
}

export function useSaveContract() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }) => {
      const body = cuerpo(data)
      // Con FormData el navegador pone el boundary; el JSON por defecto lo rompería.
      const config = body instanceof FormData ? { headers: { 'Content-Type': undefined } } : undefined
      return (id
        ? client.patch(`/api/contracts/${id}/`, body, config)
        : client.post('/api/contracts/', body, config)
      ).then((r) => r.data)
    },
    onSuccess: () => invalidar(qc),
  })
}

export function useDeleteContract() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => client.delete(`/api/contracts/${id}/`),
    onSuccess: () => invalidar(qc),
  })
}

export const CONTRACT_KINDS = [
  { value: 'MAINTENANCE', label: 'Contrato de mantenimiento' },
  { value: 'WARRANTY', label: 'Garantía de equipos' },
]

export const CONTRACT_STATUS = {
  ACTIVE: { label: 'Vigente', className: 'bg-green-50 text-green-700' },
  EXPIRING: { label: 'Por vencer', className: 'bg-amber-50 text-amber-800' },
  EXPIRED: { label: 'Vencido', className: 'bg-red-50 text-red-700' },
  UPCOMING: { label: 'Próximo', className: 'bg-blue-50 text-blue-700' },
}
