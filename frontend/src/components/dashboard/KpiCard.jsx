const COLOR_STYLES = {
  green:  { value: 'text-green-700',  dot: 'bg-green-500',  glow: 'bg-green-400' },
  yellow: { value: 'text-amber-700',  dot: 'bg-amber-500',  glow: 'bg-amber-400' },
  red:    { value: 'text-red-700',    dot: 'bg-red-500',    glow: 'bg-red-400' },
  blue:   { value: 'text-brand-700',  dot: 'bg-brand-500',  glow: 'bg-brand-400' },
  gray:   { value: 'text-gray-800',   dot: 'bg-gray-400',   glow: 'bg-gray-400' },
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
    <article className="card relative overflow-hidden p-5">
      {/* Halo desplazado fuera de la esquina: rompe la simetria de la tarjeta
          y tine la superficie sin recurrir a la barra lateral de color. */}
      <span
        className={`absolute -right-10 -top-10 h-28 w-28 rounded-full blur-2xl opacity-[0.14] ${styles.glow}`}
        aria-hidden="true"
      />

      <div className="relative flex items-center gap-2">
        <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${styles.dot}`} aria-hidden="true" />
        <p className="label-meta">{title}</p>
      </div>

      <p className={`relative mt-3 text-[2.125rem] leading-none stat-value ${styles.value}`}>
        {value}
      </p>

      {subtitle && <p className="relative mt-2.5 text-sm text-gray-500">{subtitle}</p>}

      {trend != null && trend !== '' && (
        <div
          className={`relative mt-3 inline-flex items-center gap-1 px-2 py-0.5 rounded-md
            text-xs font-medium ring-1 ring-inset ${
              trendUp
                ? 'bg-green-50 text-green-800 ring-green-200'
                : 'bg-red-50 text-red-800 ring-red-200'
            }`}
        >
          <svg className="w-3 h-3" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
            {trendUp ? <path d="M6 2l4 6H2z" /> : <path d="M6 10L2 4h8z" />}
          </svg>
          <span className="tabular-nums">{trend}</span>
        </div>
      )}
    </article>
  )
}
