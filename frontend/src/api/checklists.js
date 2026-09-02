import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'

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

export function useChecklistResponse(id) {
  return useQuery({
    queryKey: ['checklist-responses', id],
    queryFn: () => client.get(`/api/checklists/responses/${id}/`).then((r) => r.data),
    enabled: !!id,
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
