import { Link } from 'react-router-dom'

import { CHART } from '../../constants/palette'
import { shares } from '../../utils/dashboardView'
import Panel from './Panel'

const ROWS = [
  { key: 'overdue', label: 'Vencido', hint: 'Tarea preventiva pasada de fecha', color: CHART.red },
  { key: 'due_soon', label: 'Por vencer', hint: 'Vence en los próximos 30 días', color: CHART.amber },
  { key: 'on_time', label: 'Al día', hint: 'Sin tareas vencidas ni próximas', color: CHART.green },
  { key: 'no_plan', label: 'Sin protocolo', hint: 'Activos en servicio sin plan activo', color: CHART.neutral },
]

/**
 * Estado de los activos según sus tareas preventivas: una barra apilada con la
 * proporción y, debajo, cada categoría con su cifra y un clic a la lista.
 */
export default function AssetStatusPanel({ status, loading, links }) {
  const items = ROWS.map((r) => ({ ...r, value: status?.[r.key] ?? 0 }))
  const segs = shares(items)
  return (
    <Panel title="Estado de activos" action={<span className="text-xs text-gray-500">{status?.total ?? 0} en servicio</span>}>
      <div className="p-5">
        {loading ? (
          <div className="h-3 rounded-full bg-gray-100 animate-pulse" />
        ) : (
          <div
            role="img"
            aria-label={items.map((i) => `${i.label}: ${i.value}`).join(', ')}
            className="flex h-3 gap-0.5 overflow-hidden rounded-full bg-gray-100"
          >
            {segs.map((s) => (
              <span key={s.key} style={{ width: `${s.pct}%`, backgroundColor: s.color }} />
            ))}
          </div>
        )}
        <ul className="mt-4 divide-y divide-gray-100">
          {items.map((i) => (
            <li key={i.key}>
              <Link
                to={links[i.key]}
                className="flex items-center gap-3 py-2.5 -mx-2 px-2 rounded-lg hover:bg-gray-50 transition-colors
                  focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/25"
              >
                <span className="h-2.5 w-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: i.color }} aria-hidden="true" />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-gray-800">{i.label}</span>
                  <span className="block text-xs text-gray-500 truncate">{i.hint}</span>
                </span>
                <span className="text-lg stat-value text-gray-800">{loading ? '–' : i.value}</span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </Panel>
  )
}
