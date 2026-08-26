const COLOR_STYLES = {
  green:  { value: 'text-green-600',  accent: 'bg-green-500' },
  yellow: { value: 'text-amber-600',  accent: 'bg-amber-500' },
  red:    { value: 'text-red-600',    accent: 'bg-red-500' },
  blue:   { value: 'text-blue-600',   accent: 'bg-blue-500' },
  gray:   { value: 'text-gray-700',   accent: 'bg-gray-400' },
}

export default function KpiCard({
  title,
  value,
  subtitle,
  trend,
  trendDirection,
  color = 'gray',
}) {
  const styles = COLOR_STYLES[color] ?? COLOR_STYLES.gray
  const trendUp = trendDirection === 'up'

  return (
    <div className="relative bg-white rounded-xl border border-gray-200 shadow-sm p-5 overflow-hidden">
      <span className={`absolute inset-y-0 left-0 w-1 ${styles.accent}`} aria-hidden="true" />
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{title}</p>
      <p className={`mt-2 text-3xl font-bold leading-none ${styles.value}`}>{value}</p>
      {subtitle && <p className="mt-2 text-sm text-gray-500">{subtitle}</p>}
      {trend != null && trend !== '' && (
        <div
          className={`mt-3 inline-flex items-center gap-1 text-xs font-semibold ${
            trendUp ? 'text-green-600' : 'text-red-600'
          }`}
        >
          <svg className="w-3.5 h-3.5" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
            {trendUp ? <path d="M6 2l4 6H2z" /> : <path d="M6 10L2 4h8z" />}
          </svg>
          <span>{trend}</span>
        </div>
      )}
    </div>
  )
}
