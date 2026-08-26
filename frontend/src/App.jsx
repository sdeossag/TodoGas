import { useEffect } from 'react'
import { RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Capacitor } from '@capacitor/core'
import { router } from './router/index'
import { initDB } from './db/database'
import { initFCM } from './notifications/fcm'
import useAuthStore from './store/authStore'
import useNetworkStore from './store/networkStore'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
})

function AppBootstrap({ children }) {
  const loadUser = useAuthStore((s) => s.loadUser)
  const initNetworkListener = useNetworkStore((s) => s.initNetworkListener)

  useEffect(() => {
    loadUser()

    // Deliberadamente en paralelo y sin encadenar: la deteccion de red no
    // puede depender de que SQLite arranque. Si la base falla, el banner
    // offline tiene que seguir avisando igualmente. Los repositorios ya
    // esperan a initDB() por su cuenta cuando alguien los usa.
    initNetworkListener()
    initDB()

    // Push solo tiene sentido en el APK. En web el plugin no esta disponible.
    if (Capacitor.isNativePlatform()) {
      initFCM()
    }
  }, [loadUser, initNetworkListener])

  return children
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppBootstrap>
        <RouterProvider router={router} />
      </AppBootstrap>
    </QueryClientProvider>
  )
}
