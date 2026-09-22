import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'
import { getOfflineChecklistResponse, saveChecklistResponse } from '../db/repositories'
import useNetworkStore from '../store/networkStore'

export function useChecklistTemplates(params = {}) {
  return useQuery({
    queryKey: ['checklist-templates', params],
    queryFn: () => fetchAllPages(client, '/api/checklists/templates/', params),
  })
}

export function useChecklistTemplate(id) {
  return useQuery({
    queryKey: ['checklist-templates', id],
    queryFn: () => client.get(`/api/checklists/templates/${id}/`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCreateChecklistTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/checklists/templates/', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['checklist-templates'] }),
  })
}

export function usePublishVersion(templateId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) =>
      client.post(`/api/checklists/templates/${templateId}/publish-version/`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['checklist-templates', templateId] })
      qc.invalidateQueries({ queryKey: ['checklist-templates'] })
    },
  })
}

export function useCreateChecklistResponse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/checklists/responses/', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['checklist-responses'] }),
  })
}

/**
 * Checklist de una tarea. Sin red sale de SQLite, con las respuestas que el
 * tecnico escribio en el telefono encima de lo descargado.
 */
export function useChecklistResponse(id) {
  const isOnline = useNetworkStore((s) => s.isOnline)
  return useQuery({
    queryKey: ['checklist-responses', id, isOnline ? 'online' : 'offline'],
    queryFn: async () => {
      if (!isOnline) {
        const respuesta = await getOfflineChecklistResponse(id)
        if (!respuesta) {
          throw new Error('Este checklist no está descargado. Ábrelo con conexión para trabajarlo sin red.')
        }
        return respuesta
      }
      const { data } = await client.get(`/api/checklists/responses/${id}/`)
      saveChecklistResponse(data).catch((error) =>
        console.warn('[offline] no se pudo guardar el checklist:', error?.message ?? error)
      )
      return data
    },
    enabled: !!id,
    placeholderData: (previous) => previous,
    // Sin red lee SQLite. Con el modo por defecto ('online') TanStack pausa la
    // consulta en cuanto navigator.onLine es false y nunca llega a leerla.
    networkMode: 'always',
  })
}

export function useSubmitField(responseId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) =>
      client.post(`/api/checklists/responses/${responseId}/submit-field/`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['checklist-responses', responseId] }),
  })
}

export function useCompleteChecklist(responseId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      client.post(`/api/checklists/responses/${responseId}/complete/`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['checklist-responses', responseId] })
      qc.invalidateQueries({ queryKey: ['work-orders'] })
    },
  })
}
