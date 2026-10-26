import { CHART } from '../../constants/palette'
import { shares } from '../../utils/dashboardView'
import EmptyState from '../ui/EmptyState'
import Panel from './Panel'

const KINDS = [
  { key: 'PREVENTIVE', label: 'Preventivo', color: CHART.brand },
  { key: 'CORRECTIVE', label: 'Correctivo', color: CHART.brandSoft },
  { key: 'OTHER', label: 'Otros', color: CHART.neutral },
]

/** OTs del periodo según lo que el catálogo de tipos dice que cuentan (sin canceladas). */
export default function OtsByKindPanel({ data, loading, days }) {
  const items = KINDS.map((k) => ({ ...k, value: data?.[k.key] ?? 0 }))
  const total = items.reduce((a, i) => a + i.value, 0)
  return (
    <Panel title="OTs por tipo" action={<span className="text-xs text-gray-500">Últimos {days} días</span>}>
      <div className="p-5">
        {loading ? (
          <div className="h-3 rounded-full bg-gray-100 animate-pulse" />
        ) : total === 0 ? (
          <EmptyState compact icon="workOrder" title="Sin órdenes en el periodo"
            description="Amplía el periodo o quita el filtro de hospital." />
        ) : (
          <>
            <div role="img" aria-label={items.map((i) => `${i.label}: ${i.value}`).join(', ')}
              className="flex h-3 gap-0.5 overflow-hidden rounded-full bg-gray-100">
              {shares(items).map((s) => (
                <span key={s.key} style={{ width: `${s.pct}%`, backgroundColor: s.color }} />
              ))}
            </div>
            <ul className="mt-4 divide-y divide-gray-100">
              {items.map((i) => (
                <li key={i.key} className="flex items-center gap-3 py-2.5">
                  <span className="h-2.5 w-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: i.color }} aria-hidden="true" />
                  <span className="flex-1 text-sm text-gray-700">{i.label}</span>
                  <span className="text-xs text-gray-500 tabular-nums">{Math.round((i.value / total) * 100)}%</span>
                  <span className="w-10 text-right text-sm font-semibold tabular-nums text-gray-800">{i.value}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </Panel>
  )
}
