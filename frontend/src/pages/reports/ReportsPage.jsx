import { useState } from 'react'
import useAuthStore from '../../store/authStore'
import { useReports, useReportDownload } from '../../api/reports'
import { useGenerateConsolidatedReport } from '../../api/dashboard'
import { useHospitals } from '../../api/assets'
import EmptyState from '../../components/ui/EmptyState'
import { formatWoCode } from '../../utils/workOrder'

const TASK_TYPES = [
  { value: 'PREVENTIVE', label: 'Preventivo' },
  { value: 'CORRECTIVE', label: 'Correctivo' },
  { value: 'VERIFICATION', label: 'Verificacion' },
  { value: 'INSTALLATION', label: 'Instalacion' },
  { value: 'DELIVERY', label: 'Entrega' },
]

function Spinner({ small }) {
  return (
    <svg
      className={`animate-spin ${small ? 'h-4 w-4' : 'h-8 w-8'} text-brand`}
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

function ConsolidatedReportForm() {
  const { data: hospitals = [] } = useHospitals()
  const hospitalList = Array.isArray(hospitals) ? hospitals : hospitals?.results ?? []
  const generateMut = useGenerateConsolidatedReport()

  const [form, setForm] = useState({
    hospital_id: '',
    date_from: '',
    date_to: '',
    task_type: '',
  })
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  function handleSubmit(e) {
    e.preventDefault()
    generateMut.mutate(form)
  }

  const errorDetail = generateMut.error?.response?.data?.detail

  return (
    <section className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
      <h2 className="text-sm font-semibold text-gray-700 mb-1">Reporte consolidado</h2>
      <p className="text-xs text-gray-500 mb-4">
        Genera un PDF con todas las ordenes de un periodo. Se envia por correo al terminar.
      </p>

      <form onSubmit={handleSubmit} className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Hospital</label>
          <select
            value={form.hospital_id}
            onChange={(e) => set('hospital_id', e.target.value)}
            className="input-field w-56"
          >
            <option value="">Todos</option>
            {hospitalList.map((h) => (
              <option key={h.id} value={h.id}>{h.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Desde</label>
          <input
            type="date"
            required
            value={form.date_from}
            onChange={(e) => set('date_from', e.target.value)}
            className="input-field w-40"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Hasta</label>
          <input
            type="date"
            required
            value={form.date_to}
            onChange={(e) => set('date_to', e.target.value)}
            className="input-field w-40"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Tipo de OT</label>
          <select
            value={form.task_type}
            onChange={(e) => set('task_type', e.target.value)}
            className="input-field w-44"
          >
            <option value="">Todos</option>
            {TASK_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={generateMut.isPending}
          className="btn-primary inline-flex items-center gap-2"
        >
          {generateMut.isPending && <Spinner small />}
          Generar reporte consolidado
        </button>
      </form>

      {generateMut.isSuccess && (
        <div className="mt-4 px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-green-800 text-sm">
          Reporte en generacion. Recibiras un email cuando este listo.
        </div>
      )}
      {generateMut.isError && (
        <div className="mt-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {errorDetail || 'No se pudo generar el reporte consolidado.'}
        </div>
      )}
    </section>
  )
}

export default function ReportsPage() {
  const role = useAuthStore((s) => s.user?.role)
  const [woNumber, setWoNumber] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [appliedFilters, setAppliedFilters] = useState({})

  const { data: reports = [], isLoading, isError } = useReports(appliedFilters)
  const downloadMut = useReportDownload()

  function handleApply(e) {
    e.preventDefault()
    const filters = {}
    if (woNumber.trim()) filters.wo_number = woNumber.trim()
    if (dateFrom) filters.date_from = dateFrom
    if (dateTo) filters.date_to = dateTo
    setAppliedFilters(filters)
  }

  function handleClear() {
    setWoNumber('')
    setDateFrom('')
    setDateTo('')
    setAppliedFilters({})
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900 mb-1">Reportes</h1>
        <p className="text-sm text-gray-500">Reportes de servicio generados al completar ordenes de trabajo</p>
      </div>

      {role === 'ADMIN' && <ConsolidatedReportForm />}

      {/* Filtros */}
      <form
        onSubmit={handleApply}
        className="bg-white rounded-xl border border-gray-200 shadow-card p-4"
      >
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">N° OT</label>
            <input
              type="text"
              value={woNumber}
              onChange={(e) => setWoNumber(e.target.value)}
              placeholder="Ej: 42"
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 w-28"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Desde</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Hasta</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              className="px-4 py-1.5 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light transition-colors"
            >
              Filtrar
            </button>
            {Object.keys(appliedFilters).length > 0 && (
              <button
                type="button"
                onClick={handleClear}
                className="px-3 py-1.5 text-sm text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                Limpiar
              </button>
            )}
          </div>
        </div>
      </form>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Spinner />
          </div>
        ) : isError ? (
          <div className="text-center py-16 text-red-600 text-sm">
            No se pudo cargar los reportes. Revisa tu conexión e intenta de nuevo.
          </div>
        ) : reports.length === 0 ? (
          <EmptyState
            icon="report"
            title="Sin reportes para estos filtros"
            description="Amplia el rango de fechas o quita alguno de los filtros para ver mas resultados."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr className="text-left text-xs font-medium text-gray-500">
                  <th className="px-4 py-3">OT</th>
                  <th className="px-4 py-3">Titulo</th>
                  <th className="px-4 py-3">Hospital</th>
                  <th className="px-4 py-3">Generado</th>
                  <th className="px-4 py-3">Hash</th>
                  <th className="px-4 py-3">Envios</th>
                  <th className="px-4 py-3 text-right">Accion</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {reports.map((report) => {
                  const wo = report.work_order
                  const successLogs = (report.send_logs || []).filter((l) => l.was_successful)
                  return (
                    <tr key={report.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-mono text-xs text-gray-600 whitespace-nowrap">
                        {formatWoCode(wo)}
                      </td>
                      <td className="px-4 py-3 text-gray-800 max-w-[180px] truncate">
                        {report.title || wo?.title || '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs truncate max-w-[120px]">
                        {wo?.hospital?.name || '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                        {new Date(report.generated_at).toLocaleString('es-CO')}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-500">
                        {report.file_hash ? `${report.file_hash.slice(0, 12)}...` : '—'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          title={`${successLogs.length} envio(s) exitoso(s)`}
                          className={`text-xs font-medium ${successLogs.length > 0 ? 'text-green-600' : 'text-gray-500'}`}
                        >
                          {successLogs.length}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => downloadMut.mutate(report.id)}
                          disabled={downloadMut.isPending}
                          className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded bg-brand/10 text-brand hover:bg-brand/20 disabled:opacity-60 whitespace-nowrap"
                        >
                          {downloadMut.isPending ? <Spinner small /> : null}
                          Descargar
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
