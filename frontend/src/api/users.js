import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'

/**
 * Las mutaciones aceptan el id al crear el hook o dentro de las variables de
 * mutate(). Lo segundo es lo que usa la tabla: un solo hook a nivel de pagina
 * en vez de uno por fila, que romperia las reglas de los hooks.
 */
const resolveId = (bound, vars) => vars?.id ?? bound

export function useUsers(params = {}) {
  return useQuery({
    queryKey: ['users', params],
    queryFn: () => fetchAllPages(client, '/api/users/', params),
  })
}

export function useUser(id) {
  return useQuery({
    queryKey: ['users', id],
    queryFn: () => client.get(`/api/users/${id}/`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload) => client.post('/api/users/', payload).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
    },
  })
}

export function useUpdateUser(boundId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...payload }) =>
      client.patch(`/api/users/${resolveId(boundId, { id })}/`, payload).then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['users', resolveId(boundId, vars)] })
      qc.invalidateQueries({ queryKey: ['users'] })
    },
  })
}

export function useDeactivateUser(boundId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars) =>
      client.post(`/api/users/${resolveId(boundId, vars)}/deactivate/`).then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['users', resolveId(boundId, vars)] })
      qc.invalidateQueries({ queryKey: ['users'] })
    },
  })
}

export function useResetPassword(boundId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars) =>
      client.post(`/api/users/${resolveId(boundId, vars)}/reset-password/`).then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['users', resolveId(boundId, vars)] })
    },
  })
}
