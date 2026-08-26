import useNetworkStore from '../../store/networkStore'
import Icon from './Icon'

/**
 * Aviso permanente del estado de conectividad.
 *
 * No lleva boton de cerrar a proposito: mientras el tecnico esta sin red tiene
 * que saberlo en todo momento, porque cambia lo que puede esperar de la app.
 */
export default function OfflineBanner() {
  const isOnline = useNetworkStore((s) => s.isOnline)
  const isSyncing = useNetworkStore((s) => s.isSyncing)
  const pendingSyncCount = useNetworkStore((s) => s.pendingSyncCount)
  const offlineNotice = useNetworkStore((s) => s.offlineNotice)

  if (isOnline && !isSyncing) return null

  if (!isOnline) {
    return (
      <div
        role="status"
        className="flex items-start gap-3 px-4 sm:px-6 py-3 bg-amber-50 border-b border-amber-300 text-amber-900"
      >
        <Icon name="wifiOff" className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-600" />
        <div className="min-w-0">
          <p className="text-sm font-semibold">Sin conexion — Modo offline activo</p>
          <p className="text-xs text-amber-800 mt-0.5">
            Los cambios se sincronizaran al recuperar la conexion
            {pendingSyncCount > 0 && (
              <>
                {' '}
                <span className="font-medium">
                  ({pendingSyncCount} {pendingSyncCount === 1 ? 'elemento' : 'elementos'} en cola)
                </span>
              </>
            )}
          </p>
          {offlineNotice && (
            <p className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-green-800 bg-green-100 border border-green-200 rounded-lg px-2.5 py-1">
              <Icon name="checkCircle" className="w-3.5 h-3.5 flex-shrink-0" />
              {offlineNotice}
            </p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-3 px-4 sm:px-6 py-2.5 bg-blue-50 border-b border-blue-200 text-blue-900"
    >
      <svg
        className="animate-spin w-4 h-4 flex-shrink-0 text-blue-600"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
      </svg>
      <p className="text-sm font-medium">
        Sincronizando...{' '}
        <span className="font-normal text-blue-800">
          {pendingSyncCount} {pendingSyncCount === 1 ? 'elemento pendiente' : 'elementos pendientes'}
        </span>
      </p>
    </div>
  )
}
