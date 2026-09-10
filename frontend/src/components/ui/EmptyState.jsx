import Icon from './Icon'

/**
 * Vista de "aqui todavia no hay nada".
 *
 * Una linea de texto gris centrada no resuelve nada: si el usuario llega a una
 * tabla vacia hay que decirle por que esta vacia y cual es el siguiente paso.
 */
export default function EmptyState({
  icon = 'folder',
  title,
  description,
  action,
  compact = false,
}) {
  return (
    <div
      className={`flex flex-col items-center text-center ${compact ? 'py-10 px-6' : 'py-16 px-6'}`}
    >
      <span
        className="flex items-center justify-center w-12 h-12 rounded-xl bg-gray-100 text-gray-400 ring-1 ring-inset ring-gray-200"
        aria-hidden="true"
      >
        <Icon name={icon} className="w-6 h-6" />
      </span>

      <p className="mt-4 text-sm font-semibold text-gray-800">{title}</p>

      {description && (
        <p className="mt-1.5 max-w-[42ch] text-sm text-gray-500 prose-nums">{description}</p>
      )}

      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
