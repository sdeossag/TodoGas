import { QueryClient } from '@tanstack/react-query'

/**
 * Cliente de TanStack compartido. Vive aparte de App.jsx para que la
 * sincronizacion offline (networkStore) pueda refrescar las pantallas al
 * terminar de subir lo que el tecnico hizo sin red.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
})
