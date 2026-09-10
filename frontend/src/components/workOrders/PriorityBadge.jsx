import Badge from '../ui/Badge'

const PRIORITY_CONFIG = {
  HIGH:   { label: 'Alta',  tone: 'danger' },
  MEDIUM: { label: 'Media', tone: 'warning' },
  LOW:    { label: 'Baja',  tone: 'neutral' },
}

export default function PriorityBadge({ priority }) {
  const { label, tone } = PRIORITY_CONFIG[priority] ?? { label: priority, tone: 'neutral' }
  // Baja no lleva punto: la prioridad normal no tiene por que llamar la
  // atencion, solo las excepciones (alta y media) necesitan color.
  return <Badge tone={tone} dot={priority !== 'LOW'}>{label}</Badge>
}
