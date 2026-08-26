const PRIORITY_CONFIG = {
  HIGH:   { label: 'Alta',  cls: 'bg-red-100 text-red-700' },
  MEDIUM: { label: 'Media', cls: 'bg-amber-100 text-amber-700' },
  LOW:    { label: 'Baja',  cls: 'bg-green-100 text-green-700' },
}

export default function PriorityBadge({ priority }) {
  const { label, cls } = PRIORITY_CONFIG[priority] ?? { label: priority, cls: 'bg-gray-100 text-gray-500' }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${cls}`}>
      {label}
    </span>
  )
}
