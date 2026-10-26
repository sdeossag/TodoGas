import { Link } from 'react-router-dom'

import { CHART } from '../../constants/palette'
import EmptyState from '../ui/EmptyState'
import Panel from './Panel'

const SEVERITIES = [
  { key: 'CRITICAL', label: 'Crítica', color: CHART.red },
  { key: 'HIGH', label: 'Alta', color: CHART.amber },
  { key: 'MEDIUM', label: 'Media', color: CHART.amberSoft },
  { key: 'LOW', label: 'Baja', color: CHART.neutral },
]

/** Hallazgos que esperan decisión, por severidad; cada barra abre la bandeja filtrada. */
export default function OpenFindingsPanel({ data, loading, hospitalId }) {
  const max = Math.max(1, ...SEVERITIES.map((s) => data?.by_severity?.[s.key] ?? 0))
  const link = (severity) => {
    const qs = new URLSearchParams({ status: 'PENDING' })
    if (severity) qs.set('severity', severity)
    if (hospitalId) qs.set('hospital_id', hospitalId)
    return `/hallazgos?${qs.toString()}`
  }
  return (
    <Panel
      title="Hallazgos abiertos"
      action={<Link to={link()} className="btn-link text-sm">Ver bandeja</Link>}
    >
      <div className="p-5">
        {loading ? (
          <div className="space-y-3">{[...Array(4)].map((_, i) => <div key={i} className="h-6 rounded bg-gray-100 animate-pulse" />)}</div>
        ) : !data?.total ? (
          <EmptyState compact icon="checkCircle" title="Sin hallazgos por decidir"
            description="Todo lo que reportaron los técnicos ya tiene decisión." />
        ) : (
          <>
            <ul className="space-y-1">
              {SEVERITIES.map((s) => {
                const n = data.by_severity[s.key] ?? 0
                return (
                  <li key={s.key}>
                    <Link to={link(s.key)}
                      className="flex items-center gap-3 py-1.5 -mx-2 px-2 rounded-lg hover:bg-gray-50 transition-colors
                        focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/25">
                      <span className="w-14 text-sm text-gray-600">{s.label}</span>
                      <span className="h-2.5 flex-1 rounded-full bg-gray-100" aria-hidden="true">
                        <span className="block h-full rounded-full" style={{ width: `${(n / max) * 100}%`, backgroundColor: s.color }} />
                      </span>
                      <span className="w-8 text-right text-sm font-semibold tabular-nums text-gray-800">{n}</span>
                    </Link>
                  </li>
                )
              })}
            </ul>
            {data.out_of_service > 0 && (
              <p className="mt-3 text-sm text-red-700">
                {data.out_of_service} {data.out_of_service === 1 ? 'deja' : 'dejan'} el equipo fuera de servicio.
              </p>
            )}
          </>
        )}
      </div>
    </Panel>
  )
}
