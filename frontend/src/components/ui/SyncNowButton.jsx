import { useEffect, useRef, useState } from 'react'
import useNetworkStore from '../../store/networkStore'
import Icon from './Icon'
import {
  botonDeshabilitado,
  mensajeResultado,
  textoBoton,
  textoUltimaSincronizacion,
} from '../../utils/sincronizarAhora'

const MENSAJE_MS = 4000

const COLOR_MENSAJE = {
  ok: 'text-green-700',
  aviso: 'text-amber-700',
  error: 'text-red-700',
}

/**
 * Boton "Sincronizar ahora" de la cabecera. Sube lo pendiente y vuelve a pedir
 * los datos al servidor. La app no tiene sistema de avisos global (solo el
 * banner), asi que el resultado se muestra como texto temporal en el boton.
 */
export default function SyncNowButton() {
  const isOnline = useNetworkStore((s) => s.isOnline)
  const isSyncing = useNetworkStore((s) => s.isSyncing)
  const pendingSyncCount = useNetworkStore((s) => s.pendingSyncCount)
  const lastSyncAt = useNetworkStore((s) => s.lastSyncAt)
  const triggerSync = useNetworkStore((s) => s.triggerSync)

  const [mensaje, setMensaje] = useState(null)
  // Re-renderiza cada 30 s para que "hace X min" no se quede viejo.
  const [ahora, setAhora] = useState(() => Date.now())
  const timer = useRef(null)

  useEffect(() => {
    const id = setInterval(() => setAhora(Date.now()), 30000)
    return () => {
      clearInterval(id)
      if (timer.current) clearTimeout(timer.current)
    }
  }, [])

  const deshabilitado = botonDeshabilitado({ isOnline, isSyncing })
  const ultima = textoUltimaSincronizacion(lastSyncAt, ahora)
  const etiqueta = textoBoton({ isOnline, isSyncing })

  const handleClick = async () => {
    if (deshabilitado) return
    await triggerSync({ refrescar: true })
    // Se lee el store al terminar: el estado capturado arriba ya es viejo.
    const { lastSyncError, pendingSyncCount: quedan } = useNetworkStore.getState()
    setMensaje(mensajeResultado({ error: lastSyncError, pendientes: quedan }))
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setMensaje(null), MENSAJE_MS)
  }

  const title = !isOnline ? `Sin conexión. ${ultima}` : ultima

  return (
    <div className="flex flex-col items-end">
      <button
        type="button"
        onClick={handleClick}
        disabled={deshabilitado}
        aria-disabled={deshabilitado}
        aria-busy={isSyncing}
        aria-label={`${etiqueta}${pendingSyncCount > 0 ? `, ${pendingSyncCount} pendientes` : ''}. ${ultima}`}
        title={title}
        className="relative flex items-center gap-1.5 min-h-[44px] min-w-[44px] justify-center px-2.5 rounded-lg text-sm text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900 active:bg-gray-200 disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/25"
      >
        <Icon
          name={isOnline ? 'sync' : 'wifiOff'}
          className={`w-5 h-5 flex-shrink-0 ${isSyncing ? 'animate-spin' : ''}`}
        />
        <span className="hidden md:inline">{etiqueta}</span>
        {pendingSyncCount > 0 && (
          <span
            className="min-w-[1.25rem] h-5 px-1 rounded-full bg-amber-500 text-white text-xs font-semibold flex items-center justify-center"
            aria-hidden="true"
          >
            {pendingSyncCount}
          </span>
        )}
      </button>
      <span
        role="status"
        aria-live="polite"
        className={`text-[11px] leading-tight max-w-[12rem] text-right ${
          mensaje ? COLOR_MENSAJE[mensaje.tipo] : 'sr-only'
        }`}
      >
        {mensaje?.texto ?? ''}
      </span>
    </div>
  )
}
