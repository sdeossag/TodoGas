const SIZES = {
  sm: { bar: 'h-1.5', text: 'text-xs' },
  md: { bar: 'h-2.5', text: 'text-sm' },
  lg: { bar: 'h-4',   text: 'text-base' },
}

export function complianceColor(percentage) {
  if (percentage == null) return '#9ca3af'
  if (percentage >= 80) return '#16a34a'
  if (percentage >= 50) return '#ca8a04'
  return '#dc2626'
}

export default function ComplianceBar({ percentage, label, size = 'md' }) {
  const s = SIZES[size] ?? SIZES.md
  const hasData = percentage != null
  const color = complianceColor(percentage)
  const width = hasData ? Math.min(100, Math.max(0, percentage)) : 100

  return (
    <div className="w-full">
      <div className={`flex items-center justify-between mb-1 ${s.text}`}>
        <span className="text-gray-600">{label}</span>
        <span className="font-semibold" style={{ color }}>
          {hasData ? `${percentage}%` : 'Sin datos'}
        </span>
      </div>
      <div className={`w-full ${s.bar} bg-gray-100 rounded-full overflow-hidden`}>
        <div
          className={`${s.bar} rounded-full transition-all duration-300`}
          style={{ width: `${width}%`, backgroundColor: hasData ? color : '#e5e7eb' }}
        />
      </div>
    </div>
  )
}
