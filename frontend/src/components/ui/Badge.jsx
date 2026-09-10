/**
 * Etiqueta de estado.
 *
 * En lugar de la pastilla pastel solida de siempre, cada tono se construye con
 * un fondo muy tenue, un borde del mismo matiz y un punto de color. El punto
 * hace el trabajo cromatico, asi que el fondo puede quedarse casi neutro y la
 * tabla no se convierte en un semaforo.
 */

const TONES = {
  neutral: { surface: 'bg-gray-50 text-gray-700 ring-gray-200', dot: 'bg-gray-400' },
  info:    { surface: 'bg-blue-50 text-blue-800 ring-blue-200', dot: 'bg-blue-500' },
  warning: { surface: 'bg-amber-50 text-amber-800 ring-amber-200', dot: 'bg-amber-500' },
  success: { surface: 'bg-green-50 text-green-800 ring-green-200', dot: 'bg-green-600' },
  danger:  { surface: 'bg-red-50 text-red-800 ring-red-200', dot: 'bg-red-500' },
  brand:   { surface: 'bg-brand-50 text-brand-800 ring-brand-200', dot: 'bg-brand-600' },
}

export default function Badge({ tone = 'neutral', dot = true, className = '', children }) {
  const t = TONES[tone] ?? TONES.neutral
  return (
    <span
      className={`inline-flex items-center gap-1.5 pl-2 pr-2.5 py-1 rounded-md text-xs
        font-medium leading-none ring-1 ring-inset whitespace-nowrap ${t.surface} ${className}`}
    >
      {dot && <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${t.dot}`} aria-hidden="true" />}
      {children}
    </span>
  )
}

export { TONES }
