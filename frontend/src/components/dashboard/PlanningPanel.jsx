import { Link, useNavigate } from 'react-router-dom'
import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { CHART } from '../../constants/palette'
import usePrefersReducedMotion from '../../hooks/usePrefersReducedMotion'
import { monthLabel, pendingTasksLink } from '../../utils/dashboardView'
import EmptyState from '../ui/EmptyState'
import Panel from './Panel'

function PlanningTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-white ring-1 ring-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-medium text-gray-800">{d.long}</p>
      <p className="mt-0.5 font-mono text-gray-500">{d.count} tarea(s)</p>
    </div>
  )
}

/**
 * Tareas abiertas: las vencidas (rojo) y los próximos 6 meses, como la
 * planificación de Fracttal. Cada barra abre Tareas pendientes con ese rango.
 */
export default function PlanningPanel({ data, loading, hospitalId, today }) {
  const navigate = useNavigate()
  const reduced = usePrefersReducedMotion()

  const bars = [
    { key: 'overdue', short: 'Vencidas', long: 'Vencidas', count: data?.overdue ?? 0, ym: null, color: CHART.red },
    ...(data?.months ?? []).map((m) => ({
      key: m.month, ...monthLabel(m.month), count: m.count, ym: m.month, color: CHART.brand,
    })),
  ]
  const total = bars.reduce((a, b) => a + b.count, 0)
  const open = (bar) => navigate(pendingTasksLink({ ym: bar.ym, hospitalId, today }))

  return (
    <Panel
      title="Planificación de tareas"
      action={<Link to={pendingTasksLink({ hospitalId })} className="btn-link text-sm">Ver tareas</Link>}
    >
      <div className="p-5">
        {loading ? (
          <div className="h-60 rounded-lg bg-gray-50 animate-pulse" />
        ) : total === 0 ? (
          <EmptyState compact icon="calendar" title="Sin tareas abiertas"
            description="No hay tareas pendientes ni programadas en los próximos 6 meses." />
        ) : (
          <>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={bars} margin={{ top: 20, right: 4, left: -24, bottom: 0 }}>
                <XAxis dataKey="short" tick={{ fontSize: 12, fill: CHART.axis }}
                  axisLine={{ stroke: CHART.grid }} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: CHART.axis }}
                  axisLine={false} tickLine={false} />
                <Tooltip content={<PlanningTooltip />} cursor={{ fill: CHART.cursor }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={36}
                  isAnimationActive={!reduced} animationDuration={400}
                  cursor="pointer" onClick={(_, i) => open(bars[i])}>
                  {bars.map((b) => <Cell key={b.key} fill={b.color} />)}
                  <LabelList dataKey="count" position="top" fontSize={12} fill={CHART.axis}
                    formatter={(v) => (v ? v : '')} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <p className="mt-2 text-xs text-gray-500">
              <span className="inline-block h-2 w-2 rounded-full mr-1" style={{ backgroundColor: CHART.red }} aria-hidden="true" />
              Vencidas
              <span className="inline-block h-2 w-2 rounded-full mr-1 ml-4" style={{ backgroundColor: CHART.brand }} aria-hidden="true" />
              Por mes de vencimiento
            </p>
            {/* Misma información en tabla, para lector de pantalla y teclado. */}
            <table className="sr-only">
              <caption>Tareas abiertas por mes</caption>
              <tbody>
                {bars.map((b) => (
                  <tr key={b.key}>
                    <th scope="row"><Link to={pendingTasksLink({ ym: b.ym, hospitalId, today })}>{b.long}</Link></th>
                    <td>{b.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </Panel>
  )
}
