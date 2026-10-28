import { useEffect, useState } from 'react'
import { Capacitor } from '@capacitor/core'

import { useAcceptPrivacy, usePrivacyConsent } from '../../api/privacy'
import useAuthStore from '../../store/authStore'
import { RAZON_SOCIAL, TITULO, VERSION } from '../../legal/avisoPrivacidad'
import {
  estadoDelAviso,
  guardarAceptadaLocal,
  leerAceptadaLocal,
} from '../../utils/consentimiento'
import AvisoPrivacidad from './AvisoPrivacidad'

/**
 * Pantalla bloqueante con el aviso de privacidad (Ley 1581 de 2012). Se monta
 * una vez junto al router: sin aceptar la version vigente no se usa la app.
 * Sin respuesta del servidor no bloquea (ver utils/consentimiento).
 */
export default function ConsentGate() {
  const user = useAuthStore((s) => s.user)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const logout = useAuthStore((s) => s.logout)
  const activo = isAuthenticated && !!user?.id

  const { data, error, isLoading } = usePrivacyConsent({ enabled: activo })
  const aceptar = useAcceptPrivacy()
  const [politicaAbierta, setPoliticaAbierta] = useState(false)

  // La pagina publica del aviso (/privacidad) se puede leer sin aceptar.
  const enAviso = typeof window !== 'undefined' && window.location.pathname === '/privacidad'

  const estado = activo && !enAviso
    ? estadoDelAviso({
        cargando: isLoading,
        error,
        datos: data,
        aceptadaLocal: leerAceptadaLocal(user.id),
        versionApp: VERSION,
      })
    : 'permitir'

  // Constancia local: si luego no hay red, no se vuelve a preguntar.
  useEffect(() => {
    if (activo && data && !data.required) guardarAceptadaLocal(user.id, data.version)
  }, [activo, data, user?.id])

  if (estado === 'permitir') return null

  if (estado === 'esperar') {
    return <div className="fixed inset-0 z-[100] bg-gray-50" aria-hidden="true" />
  }

  // policy_url llega del backend (PRIVACY_POLICY_URL). Si es una URL externa se abre
  // fuera de la app; si esta vacia, la politica la publica el cliente y se muestra aqui.
  const politica = (data?.policy_url || '').trim()
  const politicaExterna = /^https?:\/\//i.test(politica)

  function verPolitica() {
    if (!politicaExterna) {
      setPoliticaAbierta((abierta) => !abierta)
      return
    }
    if (Capacitor.isNativePlatform()) {
      window.open(politica, '_system')
    } else {
      window.open(politica, '_blank', 'noopener,noreferrer')
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-gray-900/70 backdrop-blur-sm p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={TITULO}
        className="bg-white rounded-xl shadow-xl w-full max-w-xl max-h-[92vh] flex flex-col"
      >
        <div className="px-6 py-5 overflow-y-auto">
          <AvisoPrivacidad />
          <div className="mt-4 text-sm">
            <button
              type="button"
              onClick={verPolitica}
              aria-expanded={politicaExterna ? undefined : politicaAbierta}
              className="text-brand underline"
            >
              Ver la política completa
            </button>
            {!politicaExterna && politicaAbierta && (
              <p className="mt-2 text-gray-700">
                La política completa de tratamiento de datos la publica {RAZON_SOCIAL} y está
                disponible para todos los titulares.
              </p>
            )}
          </div>
          {aceptar.isError && (
            <p role="alert" className="mt-3 text-sm text-red-600">
              No se pudo registrar tu aceptación. Revisa tu conexión e inténtalo de nuevo.
            </p>
          )}
        </div>
        <div className="px-6 py-4 border-t border-gray-100 flex flex-wrap justify-end gap-3">
          <button
            type="button"
            onClick={() => logout()}
            disabled={aceptar.isPending}
            className="px-4 py-2 text-sm text-gray-600 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-60"
          >
            Cerrar sesión
          </button>
          <button
            type="button"
            onClick={() => aceptar.mutate()}
            disabled={aceptar.isPending}
            className="px-4 py-2 text-sm font-medium text-white rounded-lg bg-brand hover:bg-brand/90 disabled:opacity-60"
          >
            {aceptar.isPending ? 'Guardando...' : 'Acepto'}
          </button>
        </div>
      </div>
    </div>
  )
}
