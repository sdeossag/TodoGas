import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer,
} from 'recharts'
import useAuthStore from '../../store/authStore'
import {
  useMaintenancePlan,
  useComplianceData,
  useTriggerPlan,
  usePausePlan,
  useResumePlan,
} from '../../api/maintenance'
import Icon from '../../components/ui/Icon'

const FREQ_UNIT_LABELS = {
  DAYS: 'días', WEEKS: 'semanas', MONTHS: 'meses', YEARS: 'años',
}
const TASK_TYPE_LABELS = {
  PREVENTIVE: 'Preventivo', CORRECTIVE: 'Correctivo',
  VERIFICATION: 'Verificación', INSTALLATION: 'Instalación', DELIVERY: 'Entrega',
}
const PRIORITY_LABELS = {
  HIGH: { label: 'Alta', cls: 'bg-red-100 text-red-700' },
  MEDIUM: { label: 'Media', cls: 'bg-yellow-100 text-yellow-700' },
  LOW: { label: 'Baja', cls: 'bg-gray-100 text-gray-500' },
}

function Spinner() {
  return (
    <svg className="animate-spin h-6 w-6 text-brand" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

function formatDate(val) {
  if (!val) return '—'
  return new Date(val + 'T00:00:00').toLocaleDateString('es-CO', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

function formatDuration(dur) {
  if (!dur) return '—'
  const match = String(dur).match(/(\d+):(\d+):(\d+)/)
  if (!match) return dur
  const [, h, m] = match
  if (h === '0') return `${m} min`
  return `${h}h ${m}m`
}

export default function MaintenancePlanDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'ADMIN'

  const [tab, setTab] = useState(0)
  const [triggerResult, setTriggerResult] = useState(null)
  const [showTriggerModal, setShowTriggerModal] = useState(false)

  const { data: plan, isLoading, isError } = useMaintenancePlan(id)
  const pauseMut = usePausePlan(id)
  const resumeMut = useResumePlan(id)
  const triggerMut = useTriggerPlan(id)

  async function handleTrigger() {
    const res = await triggerMut.mutateAsync()
    setTriggerResult(res)
  }

  if (isLoading) {
    return <div className="flex justify-center py-20"><Spinner /></div>
  }
  if (isError || !plan) {
    return (
      <div className="text-center py-20 text-gray-500">
        <Icon name="warning" className="w-10 h-10 mx-auto mb-3 text-amber-500" />
        <p>No se encontró el plan</p>
        <button onClick={() => navigate('/planes-pm')} className="mt-3 text-sm text-brand hover:underline">
          Volver
        </button>
      </div>
    )
  }

  const pr = PRIORITY_LABELS[plan.priority] ?? { label: plan.priority, cls: 'bg-gray-100' }

  return (
    <div className="space-y-5 max-w-5xl">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 flex gap-1">
        <button onClick={() => navigate('/planes-pm')} className="hover:text-brand">Planes PM</button>
        <span>/</span>
        <span className="text-gray-600 truncate">{plan.name}</span>
      </nav>

      {/* Encabezado */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                plan.is_active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
              }`}>
                {plan.is_active ? 'Activo' : 'Pausado'}
              </span>
              <span className="text-xs text-gray-500">{TASK_TYPE_LABELS[plan.task_type]}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${pr.cls}`}>
                Prioridad {pr.label}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-gray-800">{plan.name}</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Cada {plan.frequency_value} {FREQ_UNIT_LABELS[plan.frequency_unit]}
            </p>
            {plan.description && (
              <p className="text-sm text-gray-500 mt-1">{plan.description}</p>
            )}
          </div>

          <div className="flex gap-2 flex-wrap">
            {isAdmin && (
              <button onClick={() => navigate(`/planes-pm/${id}/editar`)}
                className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
                Editar
              </button>
            )}
            {isAdmin && (plan.is_active ? (
              <button onClick={() => pauseMut.mutate()} disabled={pauseMut.isPending}
                className="px-4 py-2 bg-yellow-50 text-yellow-700 text-sm rounded-lg hover:bg-yellow-100 disabled:opacity-50">
                Pausar
              </button>
            ) : (
              <button onClick={() => resumeMut.mutate()} disabled={resumeMut.isPending}
                className="px-4 py-2 bg-green-50 text-green-700 text-sm rounded-lg hover:bg-green-100 disabled:opacity-50">
                Reanudar
              </button>
            ))}
            {isAdmin && (
              <button onClick={() => { setTriggerResult(null); setShowTriggerModal(true) }}
                className="px-4 py-2 bg-brand text-white text-sm rounded-lg hover:bg-brand-light">
                Disparar ahora
              </button>
            )}
          </div>
        </div>

        {/* Info grid */}
        <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-4 border-t pt-4">
          <InfoItem label="Checklist" value={
            plan.checklist_template
              ? <button onClick={() => navigate(`/checklists/${plan.checklist_template.id}/editar`)}
                  className="text-brand hover:underline text-sm">
                  {plan.checklist_template.name}
                </button>
              : '—'
          } />
          <InfoItem label="Duración estimada" value={formatDuration(plan.estimated_duration)} />
          <InfoItem label="Próximo vencimiento" value={formatDate(plan.next_due_date)} />
          <InfoItem label="Última generación"
            value={plan.last_generated_at
              ? new Date(plan.last_generated_at).toLocaleDateString('es-CO')
              : 'Nunca'} />
        </div>

        {/* Next 5 dates */}
        {plan.next_5_dates?.length > 0 && (
          <div className="mt-4 border-t pt-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">Próximas ejecuciones</p>
            <div className="flex gap-3 flex-wrap">
              {plan.next_5_dates.map((d, i) => (
                <span key={i} className="text-xs bg-brand/10 text-brand px-2 py-1 rounded-lg">
                  {i + 1}. {new Date(d + 'T00:00:00').toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' })}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="border-b flex">
          {['Activos del plan', 'Historial de ejecuciones', 'Cumplimiento'].map((t, i) => (
            <button key={t} onClick={() => setTab(i)}
              className={`px-5 py-3 text-sm font-medium transition-colors ${
                tab === i ? 'border-b-2 border-brand text-brand' : 'text-gray-500 hover:text-gray-700'
              }`}>
              {t}
            </button>
          ))}
        </div>
        <div className="p-6">
          {tab === 0 && <AssetsTab plan={plan} />}
          {tab === 1 && <ExecutionsTab plan={plan} />}
          {tab === 2 && <ComplianceTab planId={id} />}
        </div>
      </div>

      {/* Trigger modal */}
      {showTriggerModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4 space-y-4">
            {!triggerResult ? (
              <>
                <h3 className="text-lg font-semibold text-gray-800">Disparar plan</h3>
                <p className="text-sm text-gray-600">
                  Se generarán OTs para <strong>{plan.assets_count}</strong> activos inmediatamente.
                </p>
                {triggerMut.isError && <p className="text-sm text-red-500">Error al ejecutar.</p>}
                <div className="flex justify-end gap-3">
                  <button onClick={() => setShowTriggerModal(false)} className="px-4 py-2 text-sm text-gray-600">
                    Cancelar
                  </button>
                  <button onClick={handleTrigger} disabled={triggerMut.isPending}
                    className="px-5 py-2 bg-brand text-white text-sm rounded-lg hover:bg-brand-light disabled:opacity-60 flex items-center gap-2">
                    {triggerMut.isPending && <Spinner />}
                    Confirmar
                  </button>
                </div>
              </>
            ) : (
              <>
                <h3 className="text-lg font-semibold text-gray-800">Plan ejecutado</h3>
                <div className="bg-green-50 border border-green-100 rounded-lg p-4">
                  <p className="text-sm font-medium text-green-800 flex items-center gap-1.5">
                <Icon name="checkCircle" className="w-4 h-4 flex-shrink-0" />
                {triggerResult.created} OT(s) creada(s)
              </p>
                  {triggerResult.skipped > 0 && (
                    <p className="text-sm text-green-600 mt-1">{triggerResult.skipped} activo(s) omitido(s)</p>
                  )}
                </div>
                <div className="flex justify-end">
                  <button onClick={() => setShowTriggerModal(false)}
                    className="px-5 py-2 bg-brand text-white text-sm rounded-lg hover:bg-brand-light">
                    Cerrar
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function InfoItem({ label, value }) {
  return (
    <div>
      <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-0.5">{label}</p>
      <div className="text-sm text-gray-800">{value ?? '—'}</div>
    </div>
  )
}

function AssetsTab({ plan }) {
  const navigate = useNavigate()
  const assets = plan.assets ?? []
  if (assets.length === 0) {
    return <p className="text-sm text-gray-500 text-center py-8">Sin activos vinculados</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr className="text-left text-xs text-gray-500 uppercase tracking-wide">
            <th className="px-3 py-2">Código</th>
            <th className="px-3 py-2">Nombre</th>
            <th className="px-3 py-2">Hospital</th>
            <th className="px-3 py-2 text-right">Acciones</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {assets.map((a) => (
            <tr key={a.id} className="hover:bg-gray-50">
              <td className="px-3 py-2 font-mono text-xs text-gray-500">{a.code}</td>
              <td className="px-3 py-2 text-gray-800">{a.name}</td>
              <td className="px-3 py-2 text-gray-500">{a.hospital_name}</td>
              <td className="px-3 py-2 text-right">
                <button onClick={() => navigate(`/activos/${a.id}`)}
                  className="text-xs px-2 py-1 rounded bg-brand/10 text-brand hover:bg-brand/20">
                  Ver activo
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ExecutionsTab({ plan }) {
  const executions = plan.executions ?? []
  if (executions.length === 0) {
    return <p className="text-sm text-gray-500 text-center py-8">Sin ejecuciones registradas</p>
  }
  return (
    <div className="space-y-3">
      {executions.map((ex) => (
        <div key={ex.id} className="flex items-center justify-between border border-gray-100 rounded-lg p-3">
          <div>
            <p className="text-sm font-medium text-gray-800">
              {new Date(ex.executed_at).toLocaleString('es-CO')}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {ex.executed_by ? ex.executed_by.full_name : 'Sistema automático'}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm font-semibold text-brand">{ex.work_orders_created} OTs</p>
            <p className="text-xs text-gray-500">creadas</p>
          </div>
        </div>
      ))}
    </div>
  )
}

const MONTHS_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

function ComplianceTab({ planId }) {
  const { data, isLoading } = useComplianceData(planId)

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>
  if (!data) return null

  const chartData = (data.monthly ?? []).map((m) => ({
    name: `${MONTHS_ES[m.month - 1]} ${String(m.year).slice(2)}`,
    pct: m.percentage ?? 0,
    total: m.total,
    completed: m.completed,
    hasData: m.total > 0,
  }))

  function barColor(pct, hasData) {
    if (!hasData) return '#e5e7eb'
    if (pct >= 80) return '#22c55e'
    if (pct >= 50) return '#facc15'
    return '#ef4444'
  }

  function CustomTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-3 text-xs">
        <p className="font-semibold text-gray-700 mb-1">{label}</p>
        <p>Generadas: {d.total}</p>
        <p>Completadas: {d.completed}</p>
        <p>Cumplimiento: {d.hasData ? `${d.pct}%` : 'Sin datos'}</p>
      </div>
    )
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-600 mb-4">Cumplimiento últimos 12 meses</h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="pct" radius={[3, 3, 0, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={barColor(entry.pct, entry.hasData)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-3 text-xs text-gray-500">
        <span><span className="inline-block w-3 h-3 rounded bg-green-500 mr-1" />≥80%</span>
        <span><span className="inline-block w-3 h-3 rounded bg-yellow-400 mr-1" />50–79%</span>
        <span><span className="inline-block w-3 h-3 rounded bg-red-500 mr-1" />&lt;50%</span>
        <span><span className="inline-block w-3 h-3 rounded bg-gray-200 mr-1" />Sin OTs</span>
      </div>
    </div>
  )
}
