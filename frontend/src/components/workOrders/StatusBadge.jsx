const STATUS_CONFIG = {
  PENDING:     { label: 'Pendiente',    cls: 'bg-gray-100 text-gray-700' },
  IN_PROGRESS: { label: 'En proceso',   cls: 'bg-blue-100 text-blue-700' },
  IN_REVIEW:   { label: 'En revisión',  cls: 'bg-amber-100 text-amber-700' },
  COMPLETED:   { label: 'Finalizada',   cls: 'bg-green-100 text-green-700' },
  CANCELLED:   { label: 'Cancelada',    cls: 'bg-red-100 text-red-700' },
}

export default function StatusBadge({ status }) {
  const { label, cls } = STATUS_CONFIG[status] ?? { label: status, cls: 'bg-gray-100 text-gray-500' }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}
