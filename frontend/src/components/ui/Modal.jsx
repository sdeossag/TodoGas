import { useId } from 'react'
import useModalDismiss from '../../hooks/useModalDismiss'

/**
 * Ventana modal con el marco de siempre: título, botón de cerrar, Escape y
 * fondo bloqueado. El contenido (formulario y botones) lo pone quien la usa.
 */
export default function Modal({ title, subtitle, onClose, children, width = 'max-w-lg' }) {
  const titleId = useId()
  useModalDismiss(onClose)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 backdrop-blur-[2px]">
      <div role="dialog" aria-modal="true" aria-labelledby={titleId}
        className={`bg-white rounded-xl shadow-xl w-full ${width} mx-4 max-h-[90vh] overflow-y-auto`}>
        <div className="px-6 py-4 border-b flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 id={titleId} className="text-lg font-semibold text-gray-800">{title}</h2>
            {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
          </div>
          <button type="button" onClick={onClose} aria-label="Cerrar"
            className="text-gray-500 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}
