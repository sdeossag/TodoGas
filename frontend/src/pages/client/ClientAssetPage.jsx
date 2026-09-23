import { Link, useParams } from 'react-router-dom'

import { useAsset } from '../../api/assets'
import { useReportDownload } from '../../api/reports'
import { useAssetTasks } from '../../api/tasks'
import { useFindings } from '../../api/findings'
import { EstadoParaHospital, SeverityBadge } from '../../components/findings/FindingsPanel'
import Icon from '../../components/ui/Icon'
import Spinner from '../../components/ui/Spinner'
import { ASSET_STATUS_COLORS, assetStatusLabel } from '../../constants/labels'
import { formatDate } from '../../utils/maintenance'

/**
 * Un equipo visto por la biomédica del hospital: su ficha, lo que viene y
 * el historial de lo hecho con su acta (decisión del 2026-09-23). No ve las
 * OTs en curso ni las tareas anuladas; eso lo filtra el servidor.
 */
export default function ClientAssetPage() {
  const { id } = useParams()
  const { data: activo, isLoading, isError } = useAsset(id)
  const { data: tareas, isLoading: cargandoTareas } = useAssetTasks(id)
  const descargar = useReportDownload()

  if (isLoading) return <div className="flex justify-center py-20"><Spinner /></div>
  if (isError || !activo) {
    return <p className="text-center py-20 text-sm text-gray-500">No se encontró el equipo.</p>
  }

  const proximas = tareas?.open ?? []
  const historial = tareas?.history ?? []
  const ficha = [
    ['Ubicación', activo.node?.path || activo.equipment_location],
    ['Tipo', activo.asset_type],
    ['Marca', activo.manufacturer],
    ['Modelo', activo.model],
    ['Serie', activo.serial_number],
  ].filter(([, v]) => v)

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <Link to="/mis-activos" className="text-xs text-brand hover:underline">← Mis activos</Link>
        <div className="flex items-center gap-3 flex-wrap mt-1">
          <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">{activo.name}</h1>
          <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${ASSET_STATUS_COLORS[activo.status] ?? 'bg-gray-100 text-gray-500'}`}>
            {assetStatusLabel(activo.status)}
          </span>
        </div>
        <p className="text-sm text-gray-500 font-mono">{activo.code}</p>
      </div>

      {ficha.length > 0 && (
        <section className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
          <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {ficha.map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs text-gray-500">{k}</dt>
                <dd className="text-sm text-gray-800">{v}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <section className="bg-white rounded-xl border border-gray-200 shadow-card">
        <h2 className="px-5 py-4 border-b border-gray-100 font-semibold text-gray-700 text-sm">Próximos mantenimientos</h2>
        {cargandoTareas ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : proximas.length === 0 ? (
          <p className="text-center py-8 text-gray-500 text-sm">No hay mantenimientos programados para este equipo.</p>
        ) : (
          <ul className="divide-y divide-gray-50">
            {proximas.map((t) => (
              <li key={t.id} className="px-5 py-3 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-sm text-gray-800 truncate">{t.title}</p>
                  {t.plan && <p className="text-xs text-gray-500 truncate">{t.plan.name}</p>}
                </div>
                <FechaProgramada tarea={t} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <HallazgosDelEquipo assetId={id} />

      <section className="bg-white rounded-xl border border-gray-200 shadow-card">
        <h2 className="px-5 py-4 border-b border-gray-100 font-semibold text-gray-700 text-sm">Historial</h2>
        {cargandoTareas ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : historial.length === 0 ? (
          <p className="text-center py-8 text-gray-500 text-sm">Todavía no hay mantenimientos realizados.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50 text-left">
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500">Realizado</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500">Programado</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500">Mantenimiento</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500">Orden</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {historial.map((t) => (
                  <tr key={t.id}>
                    <td className="px-4 py-3 text-gray-800 whitespace-nowrap">{t.completed_at ? formatDate(t.completed_at) : '—'}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(t.scheduled_date)}</td>
                    <td className="px-4 py-3 text-gray-800">{t.title}</td>
                    <td className="px-4 py-3">
                      {t.work_order ? (
                        <Link to={`/historial/${t.work_order.id}`} className="font-mono text-xs text-brand hover:underline">
                          {t.work_order.wo_code}
                        </Link>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {t.work_order?.report_id && (
                        <button
                          type="button"
                          onClick={() => descargar.mutate(t.work_order.report_id)}
                          className="inline-flex items-center gap-1 text-xs text-brand hover:underline"
                        >
                          <Icon name="download" className="w-3.5 h-3.5" /> Acta
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

/** Lo que se encontró en el equipo en las visitas finalizadas, y en qué va. */
function HallazgosDelEquipo({ assetId }) {
  const { data: hallazgos = [] } = useFindings({ asset: assetId })
  if (!hallazgos.length) return null
  return (
    <section className="bg-white rounded-xl border border-gray-200 shadow-card">
      <h2 className="px-5 py-4 border-b border-gray-100 font-semibold text-gray-700 text-sm">Hallazgos</h2>
      <ul className="divide-y divide-gray-50">
        {hallazgos.map((f) => (
          <li key={f.id} className="px-5 py-3 space-y-1.5">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <SeverityBadge hallazgo={f} />
              <EstadoParaHospital hallazgo={f} />
            </div>
            <p className="text-sm text-gray-800">{f.description}</p>
            {f.resolved_on_site && <p className="text-xs text-green-800">Qué se hizo: {f.resolution_notes}</p>}
            <p className="text-xs text-gray-500">
              {formatDate(f.reported_at)} ·{' '}
              <Link to={`/historial/${f.work_order_info.id}`} className="text-brand hover:underline">{f.work_order_info.wo_code}</Link>
            </p>
          </li>
        ))}
      </ul>
    </section>
  )
}

export function FechaProgramada({ tarea }) {
  return (
    <span className={`text-xs whitespace-nowrap px-2 py-0.5 rounded-full ${tarea.is_overdue ? 'bg-red-50 text-red-700' : 'bg-gray-100 text-gray-600'}`}>
      {tarea.is_overdue ? 'Vencido · ' : ''}{formatDate(tarea.scheduled_date)}
    </span>
  )
}
