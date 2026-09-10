import { CHART, complianceColor } from '../../constants/palette'

const SIZES = {
  sm: { bar: 'h-1.5', text: 'text-xs' },
  md: { bar: 'h-2', text: 'text-sm' },
  lg: { bar: 'h-3', text: 'text-base' },
}

// Se reexporta para no romper los imports existentes; la definicion vive ahora
// en constants/palette.js junto al resto de colores de datos.
export { complianceColor }

export default function ComplianceBar({ percentage, label, size = 'md' }) {
  const s = SIZES[size] ?? SIZES.md
  const hasData = percentage != null
  const color = complianceColor(percentage)
  const width = hasData ? Math.min(100, Math.max(0, percentage)) : 100

  return (
    <div className="w-full">
      <div className={`flex items-baseline justify-between gap-3 mb-1.5 ${s.text}`}>
        <span className="text-gray-600 truncate">{label}</span>
        <span className="font-mono font-semibold tabular-nums flex-shrink-0" style={{ color }}>
          {hasData ? `${percentage}%` : 'Sin datos'}
        </span>
      </div>
      <div
        className={`w-full ${s.bar} bg-gray-100 rounded-full overflow-hidden`}
        role="progressbar"
        aria-valuenow={hasData ? width : undefined}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div
          className={`${s.bar} rounded-full transition-[width] duration-500 ease-spring`}
          style={{ width: `${width}%`, backgroundColor: hasData ? color : CHART.grid }}
        />
      </div>
    </div>
  )
}
