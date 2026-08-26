import { useQuery } from '@tanstack/react-query'
import client from './client'

export function useAuditLog(filters = {}) {
  return useQuery({
    queryKey: ['audit-log', filters],
    queryFn: () =>
      client.get('/api/audit/', { params: filters }).then((r) => r.data),
  })
}
