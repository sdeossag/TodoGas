import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'
import {
  clearMySignatureLocal,
  getMySignatureLocal,
  saveMySignatureLocal,
} from '../db/repositories'
import useAuthStore from '../store/authStore'
import useNetworkStore from '../store/networkStore'
import { elegirFirmaGuardada, puedeTenerFirmaGuardada } from '../utils/firmaGuardada'

export function useWorkOrderPhotos(workOrderId) {
  return useQuery({
    queryKey: ['photos', workOrderId],
    queryFn: () =>
      fetchAllPages(client, '/api/evidence/photos/', { work_order: workOrderId }),
    enabled: !!workOrderId,
  })
}

/** Corregir una foto: su descripción, u ocultarla del acta (no se borra). */
export function useUpdatePhoto(workOrderId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }) => client.patch(`/api/evidence/photos/${id}/`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['photos', workOrderId] }),
  })
}

export function useUploadPhoto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ work_order, task, finding, file, latitude, longitude, taken_at, caption, stage }) => {
      const form = new FormData()
      form.append('work_order', work_order)
      // De que activo es la foto; sin tarea va como foto de la visita.
      if (task) form.append('task', task)
      // Foto de un hallazgo: va con el equipo del hallazgo.
      if (finding) form.append('finding', finding)
      form.append('file', file)
      if (latitude != null) form.append('latitude', latitude)
      if (longitude != null) form.append('longitude', longitude)
      form.append('taken_at', taken_at)
      if (caption) form.append('caption', caption)
      if (stage) form.append('stage', stage)
      return client
        .post('/api/evidence/photos/', form, { headers: { 'Content-Type': undefined } })
        .then((r) => r.data)
    },
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['photos', variables.work_order] })
      if (variables.finding) qc.invalidateQueries({ queryKey: ['findings'] })
      qc.invalidateQueries({ queryKey: ['work-orders', variables.work_order] })
    },
  })
}

export function useWorkOrderSignatures(workOrderId) {
  return useQuery({
    queryKey: ['signatures', workOrderId],
    queryFn: () =>
      client
        .get('/api/evidence/signatures/', { params: { work_order: workOrderId } })
        .then((r) => r.data),
    enabled: !!workOrderId,
  })
}

export function useCreateSignature() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ work_order, image_data, use_saved, signer_name, signer_role, signature_type }) =>
      client
        .post('/api/evidence/signatures/', {
          work_order,
          // Con use_saved el servidor copia la firma guardada del usuario.
          ...(use_saved
            ? { use_saved: true }
            : { image_data: image_data.replace(/^data:image\/\w+;base64,/, '') }),
          signer_name,
          signer_role,
          ...(signature_type ? { signature_type } : {}),
        })
        .then((r) => r.data),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['signatures', variables.work_order] })
      qc.invalidateQueries({ queryKey: ['work-orders', variables.work_order] })
    },
  })
}

// ── Firma guardada del usuario ───────────────────────────────────────────────

/**
 * Trae la firma guardada del servidor y deja una copia en el telefono (o la
 * borra de alli si ya no existe), para poder usarla sin red.
 * Devuelve la respuesta del servidor, o null si no hubo.
 */
export async function cacheMySignature(user) {
  if (!user?.id || !puedeTenerFirmaGuardada(user.role)) return null
  try {
    const { data } = await client.get('/api/evidence/my-signature/')
    if (data?.exists && data.image_data) await saveMySignatureLocal(user.id, data.image_data)
    else await clearMySignatureLocal(user.id)
    return data
  } catch {
    return null
  }
}

/**
 * La firma guardada del usuario actual: del servidor con red, de la copia del
 * telefono sin ella. { dataUrl, origen } (ver elegirFirmaGuardada).
 */
export function useMySignature() {
  const user = useAuthStore((s) => s.user)
  const isOnline = useNetworkStore((s) => s.isOnline)
  return useQuery({
    queryKey: ['my-signature', user?.id ?? null, isOnline],
    queryFn: async () => {
      const remota = isOnline ? await cacheMySignature(user) : null
      const local = remota ? null : await getMySignatureLocal(user.id)
      return elegirFirmaGuardada({ remota, local })
    },
    enabled: !!user?.id && puedeTenerFirmaGuardada(user.role),
    staleTime: 60_000,
    // Sin red lee SQLite; con el modo por defecto la consulta se pausaria.
    networkMode: 'always',
  })
}

export function useSaveMySignature() {
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  return useMutation({
    mutationFn: (image_data) =>
      client
        .put('/api/evidence/my-signature/', {
          image_data: image_data.replace(/^data:image\/\w+;base64,/, ''),
        })
        .then((r) => r.data),
    onSuccess: async (data) => {
      await saveMySignatureLocal(user?.id, data.image_data)
      qc.invalidateQueries({ queryKey: ['my-signature'] })
    },
  })
}

export function useDeleteMySignature() {
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  return useMutation({
    mutationFn: () => client.delete('/api/evidence/my-signature/').then((r) => r.data),
    onSuccess: async () => {
      await clearMySignatureLocal(user?.id)
      qc.invalidateQueries({ queryKey: ['my-signature'] })
    },
  })
}
