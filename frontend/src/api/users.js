import { useQuery } from '@tanstack/react-query'
import client from './client'

export function useUsers(params = {}) {
  return useQuery({
    queryKey: ['users', params],
    queryFn: () => client.get('/api/users/', { params }).then((r) => r.data),
  })
}
