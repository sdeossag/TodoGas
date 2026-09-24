import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { rememberTaskTypeLabels } from '../constants/labels'

/**
 * Catálogo de tipos de tarea (decisión del 2026-09-23). `active: true` trae
 * solo los que se ofrecen en los formularios. Cada carga guarda los nombres
 * para `taskTypeLabel`, que los usa también sin red en el teléfono.
 */
export function useTaskTypes({ active = false } = {}, options = {}) {
  return useQuery({
    queryKey: ['task-types', { active }],
    queryFn: async () => {
      const { data } = await client.get('/api/task-types/', { params: active ? { active: 1 } : {} })
      rememberTaskTypeLabels(data)
      return data
    },
    staleTime: 10 * 60_000,
    ...options,
  })
}

function invalidar(qc) {
  qc.invalidateQueries({ queryKey: ['task-types'] })
}

export function useSaveTaskType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }) =>
      (id ? client.patch(`/api/task-types/${id}/`, data) : client.post('/api/task-types/', data)).then((r) => r.data),
    onSuccess: () => invalidar(qc),
  })
}

export function useDeleteTaskType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => client.delete(`/api/task-types/${id}/`),
    onSuccess: () => invalidar(qc),
  })
}

export const COUNTS_AS = [
  { value: 'PREVENTIVE', label: 'Preventivo', hint: 'Entra en el cumplimiento de protocolos' },
  { value: 'CORRECTIVE', label: 'Correctivo', hint: 'Entra en el tiempo medio de reparación' },
  { value: 'OTHER', label: 'Ninguno', hint: 'No entra en esos indicadores' },
]
