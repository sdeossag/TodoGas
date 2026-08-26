import { useNavigate } from 'react-router-dom'
import { useClientPortalSummary } from '../../api/clientPortal'
import { useReportDownload } from '../../api/reports'
import { useState } from 'react'

function Spinner() {
  return (
    <svg className="animate-spin h-8 w-8 text-brand" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

const STATUS_LABELS = {
  OPERATIONAL: 'Operacional',
  MAINTENANCE: 'En mantenimiento',
  REPAIR: 'En reparacion',
  OUT_OF_SERVICE: 'Fuera de servicio',
}
const STATUS_COLORS = {
  OPERATIONAL: 'bg-green-100 text-green-700',
  MAINTENANCE: 'bg-blue-100 text-blue-700',
  REPAIR: 'bg-amber-100 text-amber-700',
  OUT_OF_SERVICE: 'bg-red-100 text-red-600',
}
const WO_STATUS_COLORS = {
  COMPLETED: 'bg-green-100 text-green-700',
  IN_PROGRESS: 'bg-blue-100 text-blue-700',
  PENDING: 'bg-gray-100 text-gray-600',
  CANCELLED: 'bg-red-100 text-red-600',
}
const WO_STATUS_LABELS = {
  COMPLETED: 'Completada',
  IN_PROGRESS: 'En progreso',
  PENDING: 'Pendiente',
  CANCELLED: 'Cancelada',
}

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

  const { hospital, total_assets, assets_by_status, recent_work_orders, recent_reports } = data

  const statusEntries = Object.entries(assets_by_status || {}).filter(([, v]) => v > 0)

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">
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
            label={STATUS_LABELS[status] ?? status}
            value={count}
            color={STATUS_COLORS[status]}
          />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-white rounded-xl border border-gray-100 shadow-sm">
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
                    <p className="text-sm font-medium text-gray-800 truncate">
                      OT-{wo.wo_number} — {wo.title}
                    </p>
                    <p className="text-xs text-gray-500 truncate mt-0.5">
                      {wo.asset?.name ?? ''}
                    </p>
                  </div>
                  <span className={`flex-shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${WO_STATUS_COLORS[wo.status] ?? 'bg-gray-100 text-gray-500'}`}>
                    {WO_STATUS_LABELS[wo.status] ?? wo.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="bg-white rounded-xl border border-gray-100 shadow-sm">
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
                      {r.title || `Reporte OT-${r.wo_number}`}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {new Date(r.generated_at).toLocaleDateString('es-CO')}
                      {r.sha256_hash && (
                        <span className="ml-2 font-mono text-gray-500">#{r.sha256_hash.slice(0, 12)}</span>
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

function StatCard({ label, value, color }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      <p className="text-3xl font-bold text-gray-800">{value}</p>
      {color && (
        <span className={`inline-flex mt-1 text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>
          {label}
        </span>
      )}
    </div>
  )
}
