import { useEffect, useState } from 'react'
import useAuthStore from '../../store/authStore'
import { useReports, useReportDownload, useResendReportsEmail } from '../../api/reports'
import { useGenerateConsolidatedReport } from '../../api/dashboard'
import { useHospitals } from '../../api/assets'
import EmptyState from '../../components/ui/EmptyState'
import TaskTypeSelect from '../../components/ui/TaskTypeSelect'
import Modal from '../../components/ui/Modal'
import { formatWoCode } from '../../utils/workOrder'
import { apiErrorMessage } from '../../utils/apiError'
import {
  agruparPorHospital,
  alternarTodas,
  avisoLimite,
  esReenviable,
  excedeLimite,
  resumenGrupos,
  textoGrupo,
  textoSeleccion,
  todasMarcadas,
} from '../../utils/reenvioActas'

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
  const miCorreo = useAuthStore((s) => s.user?.email)

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
          <TaskTypeSelect
            value={form.task_type}
            onChange={(e) => set('task_type', e.target.value)}
            emptyLabel="Todos"
            className="input-field w-44"
          />
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
          Reporte en generacion.{' '}
          {miCorreo
            ? `Te llegará por correo a ${miCorreo} cuando esté listo.`
            : 'Te llegará por correo cuando esté listo.'}
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

function ReenvioModal({ grupos, total, mutation, onSend, onClose }) {
  const { conCorreo, sinCorreo } = resumenGrupos(grupos)
  const resultado = mutation.data
  return (
    <Modal
      title="Reenviar actas por correo"
      subtitle={resultado ? undefined : `${textoSeleccion(total)}. Los PDF van adjuntos.`}
      onClose={onClose}
    >
      {resultado ? (
        <div className="space-y-4 text-sm">
          {resultado.queued.length > 0 && (
            <div>
              <p className="font-medium text-green-700 mb-1">En camino</p>
              <ul className="space-y-1 text-gray-700">
                {resultado.queued.map((q) => (
                  <li key={q.hospital_id}>
                    <span className="font-medium">{q.hospital}</span>: {q.count}{' '}
                    {q.count === 1 ? 'acta' : 'actas'} a {q.to}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {resultado.skipped.length > 0 && (
            <div>
              <p className="font-medium text-amber-700 mb-1">No se enviaron</p>
              <ul className="space-y-1 text-gray-700">
                {resultado.skipped.map((s) => (
                  <li key={s.report_id}>
                    <span className="font-mono text-xs">{s.wo_code}</span> · {s.hospital}: {s.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="flex justify-end">
            <button type="button" onClick={onClose} className="btn-primary">Cerrar</button>
          </div>
        </div>
      ) : (
        <div className="space-y-4 text-sm">
          <ul className="divide-y divide-gray-100 border border-gray-200 rounded-lg">
            {grupos.map((g) => (
              <li key={g.hospital_id || g.name} className="px-3 py-2 flex flex-col gap-0.5">
                <span className="font-medium text-gray-800">{g.name}</span>
                <span className={g.contact_email ? 'text-gray-600' : 'text-amber-700'}>{textoGrupo(g)}</span>
              </li>
            ))}
          </ul>
          {sinCorreo > 0 && (
            <p className="text-amber-700">
              {sinCorreo} {sinCorreo === 1 ? 'acta no se enviará' : 'actas no se enviarán'} porque su hospital no tiene correo de contacto.
            </p>
          )}
          {mutation.isError && (
            <p className="px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-red-700">
              {apiErrorMessage(mutation.error, 'No se pudo reenviar las actas.')}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">
              Cancelar
            </button>
            <button type="button" onClick={onSend}
              disabled={mutation.isPending || conCorreo === 0}
              className="btn-primary inline-flex items-center gap-2 disabled:opacity-60">
              {mutation.isPending && <Spinner small />}
              Reenviar
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}

export default function ReportsPage() {
  const role = useAuthStore((s) => s.user?.role)
  const [woNumber, setWoNumber] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [appliedFilters, setAppliedFilters] = useState({})
  // Las actas de un hospital (audio3 07:12). Se aplica al elegirlo.
  const [hospital, setHospital] = useState('')
  const { data: hospitals = [] } = useHospitals()
  const hospitalList = Array.isArray(hospitals) ? hospitals : hospitals?.results ?? []

  const { data: reports = [], isLoading, isError } = useReports({
    ...appliedFilters,
    ...(hospital && { hospital_id: hospital }),
  })
  const downloadMut = useReportDownload()

  // Reenvío en bloque (solo ADMIN): la selección se vacía al cambiar los filtros.
  const isAdmin = role === 'ADMIN'
  const resendMut = useResendReportsEmail()
  const [seleccion, setSeleccion] = useState(() => new Set())
  const [confirmando, setConfirmando] = useState(false)
  useEffect(() => {
    setSeleccion(new Set())
  }, [appliedFilters, hospital])

  function alternarUna(id) {
    setSeleccion((prev) => {
      const nueva = new Set(prev)
      if (nueva.has(id)) nueva.delete(id)
      else nueva.add(id)
      return nueva
    })
  }

  function cerrarReenvio() {
    const hecho = resendMut.isSuccess
    setConfirmando(false)
    resendMut.reset()
    if (hecho) setSeleccion(new Set())
  }

  function handleApply(e) {
    e.preventDefault()
    const filters = {}
    if (woNumber.trim()) filters.wo_number = woNumber.trim()
    if (dateFrom) filters.date_from = dateFrom
    if (dateTo) filters.date_to = dateTo
    setAppliedFilters(filters)
  }

  function handleClear() {
    setHospital('')
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
          {hospitalList.length > 1 && (
            <div>
              <label className="block text-xs text-gray-500 mb-1">Hospital</label>
              <select
                value={hospital}
                onChange={(e) => setHospital(e.target.value)}
                className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 w-56"
              >
                <option value="">Todos</option>
                {hospitalList.map((h) => (
                  <option key={h.id} value={h.id}>{h.name}{h.is_active ? '' : ' (inactivo)'}</option>
                ))}
              </select>
            </div>
          )}
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
            {(Object.keys(appliedFilters).length > 0 || hospital) && (
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

      {isAdmin && seleccion.size > 0 && (
        // Abajo y fija: arriba empujaba la tabla y el siguiente clic caía en otra fila.
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-30 w-[min(44rem,calc(100%-2rem))] bg-brand text-white rounded-xl shadow-lg px-4 py-3 flex flex-wrap items-center gap-3 text-sm">
          <span className="font-medium">{textoSeleccion(seleccion.size)}</span>
          {excedeLimite(seleccion.size) && (
            <span className="text-amber-200">{avisoLimite()}</span>
          )}
          <div className="ml-auto flex gap-2">
            <button type="button" onClick={() => setConfirmando(true)}
              disabled={excedeLimite(seleccion.size)}
              className="px-3 py-1.5 rounded-lg bg-white text-brand font-medium hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed">
              Reenviar por correo
            </button>
            <button type="button" onClick={() => setSeleccion(new Set())}
              className="px-3 py-1.5 rounded-lg border border-white/40 hover:bg-white/10">
              Quitar selección
            </button>
          </div>
        </div>
      )}

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
                  {isAdmin && (
                    <th className="px-4 py-3 w-10">
                      <input
                        type="checkbox"
                        aria-label="Marcar todas las actas visibles"
                        checked={todasMarcadas(seleccion, reports)}
                        onChange={() => setSeleccion((prev) => alternarTodas(prev, reports))}
                      />
                    </th>
                  )}
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
                      {isAdmin && (
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            aria-label={`Marcar acta ${formatWoCode(wo)}`}
                            disabled={!esReenviable(report)}
                            checked={seleccion.has(report.id)}
                            onChange={() => alternarUna(report.id)}
                          />
                        </td>
                      )}
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

      {/* Espacio para que la barra fija no tape la última fila. */}
      {isAdmin && seleccion.size > 0 && <div className="h-16" aria-hidden="true" />}

      {confirmando && (
        <ReenvioModal
          grupos={agruparPorHospital(reports, seleccion)}
          total={seleccion.size}
          mutation={resendMut}
          onSend={() => resendMut.mutate([...seleccion])}
          onClose={cerrarReenvio}
        />
      )}
    </div>
  )
}
