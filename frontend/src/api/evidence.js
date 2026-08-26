import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'

export function useWorkOrderPhotos(workOrderId) {
  return useQuery({
    queryKey: ['photos', workOrderId],
    queryFn: () =>
      client.get('/api/evidence/photos/', { params: { work_order: workOrderId } }).then((r) => r.data),
    enabled: !!workOrderId,
  })
}

export function useUploadPhoto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ work_order, file, latitude, longitude, taken_at, caption }) => {
      const form = new FormData()
      form.append('work_order', work_order)
      form.append('file', file)
      if (latitude != null) form.append('latitude', latitude)
      if (longitude != null) form.append('longitude', longitude)
      form.append('taken_at', taken_at)
      if (caption) form.append('caption', caption)
      return client
        .post('/api/evidence/photos/', form, { headers: { 'Content-Type': undefined } })
        .then((r) => r.data)
    },
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['photos', variables.work_order] })
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
    mutationFn: ({ work_order, image_data, signer_name, signer_role, signature_type }) =>
      client
        .post('/api/evidence/signatures/', {
          work_order,
          image_data: image_data.replace(/^data:image\/\w+;base64,/, ''),
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
