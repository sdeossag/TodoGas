import { useQuery } from '@tanstack/react-query'
import client from './client'

export function useClientPortalSummary() {
  return useQuery({
    queryKey: ['client-portal-summary'],
    queryFn: () => client.get('/api/client-portal/summary/').then((r) => r.data),
  })
}
