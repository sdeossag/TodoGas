import Badge from '../ui/Badge'

const STATUS_CONFIG = {
  PENDING:     { label: 'Pendiente',   tone: 'neutral' },
  IN_PROGRESS: { label: 'En proceso',  tone: 'info' },
  IN_REVIEW:   { label: 'En revisión', tone: 'warning' },
  COMPLETED:   { label: 'Finalizada',  tone: 'success' },
  CANCELLED:   { label: 'Cancelada',   tone: 'danger' },
}

export default function StatusBadge({ status }) {
  const { label, tone } = STATUS_CONFIG[status] ?? { label: status, tone: 'neutral' }
  return <Badge tone={tone}>{label}</Badge>
}
