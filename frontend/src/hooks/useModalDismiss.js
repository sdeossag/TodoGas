import { useEffect } from 'react'

/**
 * Cierra un modal con Escape y bloquea el scroll del fondo mientras esta
 * abierto.
 *
 * Se registra en `keydown` de document con captura para que funcione aunque el
 * foco este dentro de un input del propio modal.
 */
export default function useModalDismiss(onClose) {
  useEffect(() => {
    if (typeof onClose !== 'function') return undefined

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        event.stopPropagation()
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown, true)

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', handleKeyDown, true)
      document.body.style.overflow = previousOverflow
    }
  }, [onClose])
}
