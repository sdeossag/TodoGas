import { useState } from 'react'

import { useReports, useReportDownload } from '../../api/reports'
import EmptyState from '../../components/ui/EmptyState'
import { formatWoCode } from '../../utils/workOrder'

/**
 * Listado de reportes del hospital del cliente.
 *
 * No hace falta filtrar por hospital: GeneratedReportViewSet ya acota la
 * consulta al hospital del usuario CLI.
 */
export default function ClientReportsPage() {
  const [downloadingId, setDownloadingId] = useState(null)
  const { data: reports = [], isLoading, isError } = useReports()
  const downloadMut = useReportDownload()

  function handleDownload(id) {
    setDownloadingId(id)
    downloadMut.mutate(id, { onSettled: () => setDownloadingId(null) })
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900 mb-1">Mis reportes</h1>
        <p className="text-sm text-gray-500">
          Reportes de servicio de las ordenes completadas en su institucion
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <svg className="animate-spin h-8 w-8 text-brand" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          </div>
        ) : isError ? (
          <div className="text-center py-16 text-red-600 text-sm">
            No se pudieron cargar los reportes. Revisa tu conexion e intenta de nuevo.
          </div>
        ) : reports.length === 0 ? (
          <EmptyState
            icon="report"
            title="Aun no hay reportes disponibles"
            description="Los informes de mantenimiento se publican aqui cuando el equipo cierra y firma una orden de trabajo."
          />
        ) : (
          <ul className="divide-y divide-gray-100">
            {reports.map((report) => (
              <li
                key={report.id}
                className="px-5 py-4 flex items-center justify-between gap-4 flex-wrap"
              >
                <div className="min-w-0 space-y-0.5">
                  <p className="text-sm font-medium text-gray-800">
                    {report.title || `Reporte ${formatWoCode(report.work_order)}`}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatWoCode(report.work_order)}
                    {' · '}
                    {new Date(report.generated_at).toLocaleDateString('es-CO')}
                  </p>
                  {report.file_hash && (
                    <p className="font-mono text-xs text-gray-500">
                      SHA-256: {report.file_hash.slice(0, 16)}...
                    </p>
                  )}
                </div>
                <button
                  onClick={() => handleDownload(report.id)}
                  disabled={downloadingId === report.id}
                  className="flex-shrink-0 px-4 py-2 bg-brand text-white text-xs font-medium rounded-lg hover:bg-brand-light disabled:opacity-60 whitespace-nowrap transition-colors"
                >
                  {downloadingId === report.id ? 'Descargando...' : 'Descargar PDF'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
