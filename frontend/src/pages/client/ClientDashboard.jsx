import { Link, useNavigate } from 'react-router-dom'
import { FechaProgramada } from './ClientAssetPage'
import { useClientPortalSummary } from '../../api/clientPortal'
import { useReportDownload } from '../../api/reports'
import { useState } from 'react'
import {
  ASSET_STATUS_COLORS,
  WO_STATUS_COLORS,
  assetStatusLabel,
  woStatusLabel,
} from '../../constants/labels'
import { EstadoDocumento } from '../../components/contracts/ContractStatus'
import Icon from '../../components/ui/Icon'
import Spinner from '../../components/ui/Spinner'
import { formatDate } from '../../utils/maintenance'
import { formatWoCode } from '../../utils/workOrder'
import { mediaUrl } from '../../api/client'


export default function ClientDashboard() {
  const navigate = useNavigate()
  const { data, isLoading, isError } = useClientPortalSummary()
  const downloadMut = useReportDownload()
  const [downloadingId, setDownloadingId] = useState(null)

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="text-center py-20 text-gray-500">
        <p className="text-sm">No se pudo cargar el resumen. Intenta recargar la pagina.</p>
      </div>
    )
  }

  const {
    hospital, total_assets, assets_by_status, recent_work_orders, recent_reports,
    upcoming = [], upcoming_total = 0, overdue_count = 0, compliance,
    recent_findings = [], open_findings_count = 0,
    contracts = [],
  } = data

  const statusEntries = Object.entries(assets_by_status || {}).filter(([, v]) => v > 0)

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">
          {hospital?.name ?? 'Panel de cliente'}
        </h1>
        {hospital?.address && (
          <p className="text-sm text-gray-500 mt-0.5">{hospital.address}</p>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Total activos" value={total_assets ?? 0} />
        {statusEntries.map(([status, count]) => (
          <StatCard
            key={status}
            label={assetStatusLabel(status)}
            value={count}
            color={ASSET_STATUS_COLORS[status]}
          />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Cumplimiento compliance={compliance} vencidos={overdue_count} />

        <section className="bg-white rounded-xl border border-gray-200 shadow-card lg:col-span-2">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-700 text-sm">Próximos mantenimientos</h2>
            {upcoming_total > upcoming.length && (
              <span className="text-xs text-gray-500">{upcoming.length} de {upcoming_total}</span>
            )}
          </div>
          {!upcoming.length ? (
            <p className="text-center py-10 text-gray-500 text-sm">No hay mantenimientos programados.</p>
          ) : (
            <ul className="divide-y divide-gray-50">
              {upcoming.map((t) => (
                <li key={t.task_id} className="px-5 py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <Link to={`/mis-activos/${t.asset.id}`} className="text-sm font-medium text-gray-800 hover:underline truncate block">
                      {t.asset.name} <span className="font-mono text-xs text-gray-500">{t.asset.code}</span>
                    </Link>
                    <p className="text-xs text-gray-500 truncate">{t.title}{t.asset.node_path ? ` · ${t.asset.node_path}` : ''}</p>
                  </div>
                  <FechaProgramada tarea={t} />
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {recent_findings.length > 0 && (
        <section className="bg-white rounded-xl border border-gray-200 shadow-card">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-700 text-sm">Hallazgos</h2>
            {open_findings_count > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-medium">
                {open_findings_count} sin corregir
              </span>
            )}
          </div>
          <ul className="divide-y divide-gray-50">
            {recent_findings.map((f) => (
              <li key={f.id} className="px-5 py-3 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <Link to={`/mis-activos/${f.asset.id}`} className="text-sm font-medium text-gray-800 hover:underline">
                    {f.asset.name} <span className="font-mono text-xs text-gray-500">{f.asset.code}</span>
                  </Link>
                  <p className="text-sm text-gray-600 truncate">{f.description}</p>
                  <p className="text-xs text-gray-500">
                    {f.severity_display}{f.out_of_service ? ' · Fuera de servicio' : ''} ·{' '}
                    <Link to={`/historial/${f.work_order.id}`} className="text-brand hover:underline">{f.work_order.wo_code}</Link>
                  </p>
                </div>
                <span className={`flex-shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${ESTADO_HALLAZGO[f.state][1]}`}>
                  {ESTADO_HALLAZGO[f.state][0]}{f.state === 'SCHEDULED' ? ` ${formatDate(f.correction_date)}` : ''}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <ContratosDelHospital contratos={contracts} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-white rounded-xl border border-gray-200 shadow-card">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-700 text-sm">Ultimas ordenes de trabajo</h2>
            <button
              onClick={() => navigate('/mis-activos')}
              className="text-xs text-brand hover:underline"
            >
              Ver mis activos
            </button>
          </div>

          {!recent_work_orders?.length ? (
            <p className="text-center py-10 text-gray-500 text-sm">Sin ordenes de trabajo recientes.</p>
          ) : (
            <ul className="divide-y divide-gray-50">
              {recent_work_orders.map((wo) => (
                <li key={wo.id} className="px-5 py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <Link to={`/historial/${wo.id}`} className="text-sm font-medium text-gray-800 hover:underline truncate block">
                      {formatWoCode(wo)} — {wo.title}
                    </Link>
                    <p className="text-xs text-gray-500 truncate mt-0.5">
                      {wo.assets?.length > 1
                        ? `${wo.assets.length} activos`
                        : (wo.assets?.[0]?.name ?? '')}
                    </p>
                  </div>
                  <span className={`flex-shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${WO_STATUS_COLORS[wo.status] ?? 'bg-gray-100 text-gray-500'}`}>
                    {woStatusLabel(wo.status)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="bg-white rounded-xl border border-gray-200 shadow-card">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-700 text-sm">Reportes recientes</h2>
          </div>

          {!recent_reports?.length ? (
            <p className="text-center py-10 text-gray-500 text-sm">Sin reportes disponibles.</p>
          ) : (
            <ul className="divide-y divide-gray-50">
              {recent_reports.map((r) => (
                <li key={r.id} className="px-5 py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">
                      {r.title || `Reporte ${formatWoCode(r)}`}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {new Date(r.generated_at).toLocaleDateString('es-CO')}
                      {r.file_hash && (
                        <span className="ml-2 font-mono text-gray-500">#{r.file_hash.slice(0, 12)}</span>
                      )}
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setDownloadingId(r.id)
                      downloadMut.mutate(r.id, { onSettled: () => setDownloadingId(null) })
                    }}
                    disabled={downloadingId === r.id}
                    className="flex-shrink-0 text-xs text-brand hover:underline disabled:opacity-50"
                  >
                    {downloadingId === r.id ? 'Descargando...' : 'Descargar'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}

/**
 * Cumplimiento de los últimos 12 meses: de lo que tocaba (fecha ya pasada),
 * cuánto se hizo y cuánto a tiempo. Lo calcula el servidor.
 */
function Cumplimiento({ compliance, vencidos }) {
  const pct = compliance?.percentage
  const color = pct == null ? 'text-gray-400' : pct >= 90 ? 'text-green-600' : pct >= 70 ? 'text-amber-600' : 'text-red-600'
  return (
    <section className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
      <h2 className="font-semibold text-gray-700 text-sm">Cumplimiento</h2>
      <p className="text-xs text-gray-500">Últimos 12 meses</p>
      <p className={`text-4xl font-bold mt-3 ${color}`}>{pct == null ? '—' : `${pct}%`}</p>
      {compliance?.planned ? (
        <p className="text-sm text-gray-600 mt-2">
          {compliance.done} de {compliance.planned} mantenimientos realizados; {compliance.on_time} a tiempo.
        </p>
      ) : (
        <p className="text-sm text-gray-500 mt-2">Aún no hay mantenimientos programados en el periodo.</p>
      )}
      {vencidos > 0 && (
        <p className="text-sm text-red-700 bg-red-50 rounded-lg px-3 py-2 mt-3">
          {vencidos === 1 ? '1 mantenimiento vencido' : `${vencidos} mantenimientos vencidos`}
        </p>
      )}
    </section>
  )
}

// Como lo entiende el hospital (igual que en la ficha del equipo).
const ESTADO_HALLAZGO = {
  RESOLVED: ['Resuelto', 'bg-green-50 text-green-700'],
  DISMISSED: ['Descartado', 'bg-gray-100 text-gray-600'],
  SCHEDULED: ['Corrección programada', 'bg-blue-50 text-blue-700'],
  OPEN: ['Pendiente de corrección', 'bg-amber-50 text-amber-700'],
}

function StatCard({ label, value, color }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-card p-4">
      <p className="text-xs font-medium text-gray-500 mb-1">{label}</p>
      <p className="text-3xl font-bold text-gray-800">{value}</p>
      {color && (
        <span className={`inline-flex mt-1 text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>
          {label}
        </span>
      )}
    </div>
  )
}

/**
 * Contratos de mantenimiento y garantías del hospital, con su vigencia y el
 * documento para descargar (decisión del 2026-09-23). Los vencidos del
 * último año se ven como historial.
 */
function ContratosDelHospital({ contratos }) {
  if (!contratos.length) return null
  return (
    <section className="bg-white rounded-xl border border-gray-200 shadow-card">
      <h2 className="px-5 py-4 border-b border-gray-100 font-semibold text-gray-700 text-sm">Contratos y garantías</h2>
      <ul className="divide-y divide-gray-50">
        {contratos.map((c) => (
          <li key={c.id} className="px-5 py-3 flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-800">{c.name}</p>
              <p className="text-xs text-gray-500">
                {c.kind_display} · {formatDate(c.start_date)} → {formatDate(c.end_date)}
              </p>
              {c.assets.length > 0 && (
                <p className="text-xs text-gray-500 mt-0.5">
                  Cubre:{' '}
                  {c.assets.slice(0, 4).map((a, i) => (
                    <span key={a.id}>
                      {i > 0 && ', '}
                      <Link to={`/mis-activos/${a.id}`} className="text-brand hover:underline">{a.name}</Link>
                    </span>
                  ))}
                  {c.assets.length > 4 && ` y ${c.assets.length - 4} más`}
                </p>
              )}
            </div>
            <div className="flex items-center gap-3 flex-shrink-0">
              <EstadoDocumento doc={c} />
              {c.file_url && (
                <a href={mediaUrl(c.file_url)} target="_blank" rel="noreferrer"
                  className="text-xs px-2 py-1 rounded bg-brand/10 text-brand hover:bg-brand/20 inline-flex items-center gap-1">
                  <Icon name="download" className="w-3.5 h-3.5" /> Documento
                </a>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
