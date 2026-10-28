import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'

/** Estado del aviso de privacidad del usuario con sesion. Sin reintentos: sin red se decide ya. */
export function usePrivacyConsent({ enabled = true } = {}) {
  return useQuery({
    queryKey: ['privacy-consent'],
    queryFn: () => client.get('/api/users/me/privacy-consent/').then((r) => r.data),
    enabled,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useAcceptPrivacy() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => client.post('/api/users/me/privacy-consent/').then((r) => r.data),
    onSuccess: (data) => qc.setQueryData(['privacy-consent'], data),
  })
}

export function useMyPersonalData() {
  return useQuery({
    queryKey: ['my-personal-data'],
    queryFn: () => client.get('/api/users/me/personal-data/').then((r) => r.data),
  })
}

/** Exporta los datos de otro usuario (solo ADMIN); deja constancia en auditoria. */
export function exportUserPersonalData(id) {
  return client.get(`/api/users/${id}/personal-data/`).then((r) => r.data)
}

export function useAnonymizeUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => client.post(`/api/users/${id}/anonymize/`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}

/** Descarga un objeto como archivo JSON desde el navegador. */
export function descargarJson(datos, nombre) {
  const blob = new Blob([JSON.stringify(datos, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nombre
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
