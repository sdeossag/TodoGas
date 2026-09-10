import { useQuery } from '@tanstack/react-query'
import client from './client'

/**
 * El endpoint es exclusivo del rol CLI: cualquier otro rol recibe 403, asi que
 * las pantallas compartidas tienen que poder desactivarlo con `enabled`.
 */
export function useClientPortalSummary({ enabled = true } = {}) {
  return useQuery({
    queryKey: ['client-portal-summary'],
    queryFn: () => client.get('/api/client-portal/summary/').then((r) => r.data),
    enabled,
  })
}
