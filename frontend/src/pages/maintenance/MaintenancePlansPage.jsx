import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import {
  useMaintenancePlans,
  useTriggerPlan,
  usePausePlan,
  useResumePlan,
} from '../../api/maintenance'
import Icon from '../../components/ui/Icon'

const TASK_TYPE_LABELS = {
  PREVENTIVE: 'Preventivo',
  CORRECTIVE: 'Correctivo',
  VERIFICATION: 'Verificación',
  INSTALLATION: 'Instalación',
  DELIVERY: 'Entrega',
}

const FREQ_UNIT_LABELS = {
  DAYS: 'días',
  WEEKS: 'semanas',
  MONTHS: 'meses',
  YEARS: 'años',
}

function Spinner() {
  return (
    <svg className="animate-spin h-5 w-5 text-brand" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

function ComplianceBar({ pct }) {
  if (pct === null || pct === undefined) {
    return <span className="text-xs text-gray-500">Sin datos</span>
  }
  const color = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-400' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-xs font-medium text-gray-600">{pct}%</span>
    </div>
  )
}

export default function MaintenancePlansPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'ADMIN'

  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [triggerPlanId, setTriggerPlanId] = useState(null)
  const [triggerResult, setTriggerResult] = useState(null)

  const params = {
    ...(statusFilter === 'active' && { is_active: true }),
    ...(statusFilter === 'inactive' && { is_active: false }),
    ...(typeFilter && { task_type: typeFilter }),
  }
  const { data: plans = [], isLoading } = useMaintenancePlans(params)

  const planForTrigger = plans.find((p) => p.id === triggerPlanId)

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Planes PM</h1>
          <p className="text-sm text-gray-500 mt-0.5">{plans.length} planes de mantenimiento</p>
        </div>
        {isAdmin && (
          <button
            onClick={() => navigate('/planes-pm/nuevo')}
            className="px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light transition-colors"
          >
            + Nuevo plan
          </button>
        )}
      </div>

      {/* Filtros */}
      <div className="flex gap-2 flex-wrap">
        {[
          { value: '', label: 'Todos' },
          { value: 'active', label: 'Activos' },
          { value: 'inactive', label: 'Pausados' },
        ].map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setStatusFilter(value)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              statusFilter === value
                ? 'bg-brand text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {label}
          </button>
        ))}
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none"
        >
          <option value="">Todos los tipos</option>
          {Object.entries(TASK_TYPE_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : plans.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <Icon name="calendar" className="w-10 h-10 mx-auto mb-3 text-gray-400" />
            <p className="font-medium">No hay planes de mantenimiento</p>
            {isAdmin && (
              <button onClick={() => navigate('/planes-pm/nuevo')} className="mt-3 text-sm text-brand hover:underline">
                + Crear el primer plan
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-3">Nombre</th>
                  <th className="px-4 py-3">Frecuencia</th>
                  <th className="px-4 py-3">Tipo</th>
                  <th className="px-4 py-3">Activos</th>
                  <th className="px-4 py-3">Cumplimiento</th>
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {plans.map((plan) => (
                  <PlanRow
                    key={plan.id}
                    plan={plan}
                    isAdmin={isAdmin}
                    onView={() => navigate(`/planes-pm/${plan.id}`)}
                    onEdit={() => navigate(`/planes-pm/${plan.id}/editar`)}
                    onTrigger={() => { setTriggerPlanId(plan.id); setTriggerResult(null) }}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal trigger */}
      {triggerPlanId && planForTrigger && (
        <TriggerModal
          plan={planForTrigger}
          result={triggerResult}
          onResult={setTriggerResult}
          onClose={() => { setTriggerPlanId(null); setTriggerResult(null) }}
        />
      )}
    </div>
  )
}

function PlanRow({ plan, isAdmin, onView, onEdit, onTrigger }) {
  const pauseMut = usePausePlan(plan.id)
  const resumeMut = useResumePlan(plan.id)

  return (
    <tr className="hover:bg-gray-50 transition-colors">
      <td className="px-4 py-3">
        <p className="font-medium text-gray-800">{plan.name}</p>
        {plan.checklist_template && (
          <p className="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
                        <Icon name="checklist" className="w-3.5 h-3.5 flex-shrink-0" />
                        {plan.checklist_template.name}
                      </p>
        )}
      </td>
      <td className="px-4 py-3 text-gray-500">
        Cada {plan.frequency_value} {FREQ_UNIT_LABELS[plan.frequency_unit] ?? plan.frequency_unit}
      </td>
      <td className="px-4 py-3 text-gray-500">{TASK_TYPE_LABELS[plan.task_type] ?? plan.task_type}</td>
      <td className="px-4 py-3 text-gray-500">{plan.assets_count}</td>
      <td className="px-4 py-3">
        <ComplianceBar pct={plan.compliance_percentage} />
      </td>
      <td className="px-4 py-3">
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            plan.is_active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
          }`}
        >
          {plan.is_active ? 'Activo' : 'Pausado'}
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="flex justify-end gap-1 flex-wrap">
          <button onClick={onView} className="text-xs px-2 py-1 rounded bg-brand/10 text-brand hover:bg-brand/20">
            Ver
          </button>
          {isAdmin && (
            <>
              <button onClick={onEdit} className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200">
                Editar
              </button>
              {plan.is_active ? (
                <button
                  onClick={() => pauseMut.mutate()}
                  disabled={pauseMut.isPending}
                  className="text-xs px-2 py-1 rounded bg-yellow-50 text-yellow-700 hover:bg-yellow-100 disabled:opacity-50"
                >
                  Pausar
                </button>
              ) : (
                <button
                  onClick={() => resumeMut.mutate()}
                  disabled={resumeMut.isPending}
                  className="text-xs px-2 py-1 rounded bg-green-50 text-green-700 hover:bg-green-100 disabled:opacity-50"
                >
                  Reanudar
                </button>
              )}
              <button
                onClick={onTrigger}
                className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100"
              >
                Disparar
              </button>
            </>
          )}
        </div>
      </td>
    </tr>
  )
}

function TriggerModal({ plan, result, onResult, onClose }) {
  const triggerMut = useTriggerPlan(plan.id)

  async function handleConfirm() {
    const res = await triggerMut.mutateAsync()
    onResult(res)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4 space-y-4">
        {!result ? (
          <>
            <h3 className="text-lg font-semibold text-gray-800">Disparar plan manualmente</h3>
            <p className="text-sm text-gray-600">
              Esto generará OTs inmediatamente para los{' '}
              <strong>{plan.assets_count}</strong> activos del plan{' '}
              <strong>"{plan.name}"</strong>. Si un activo ya tiene una OT activa, se omitirá.
            </p>
            {triggerMut.isError && (
              <p className="text-sm text-red-500">Error al disparar el plan. Intenta de nuevo.</p>
            )}
            <div className="flex justify-end gap-3 pt-1">
              <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
                Cancelar
              </button>
              <button
                onClick={handleConfirm}
                disabled={triggerMut.isPending}
                className="px-5 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60 flex items-center gap-2"
              >
                {triggerMut.isPending && <Spinner />}
                Confirmar
              </button>
            </div>
          </>
        ) : (
          <>
            <h3 className="text-lg font-semibold text-gray-800">Plan ejecutado</h3>
            <div className="bg-green-50 border border-green-100 rounded-lg p-4 space-y-1">
              <p className="text-sm font-medium text-green-800 flex items-center gap-1.5">
                <Icon name="checkCircle" className="w-4 h-4 flex-shrink-0" />
                {result.created} OT{result.created !== 1 ? 's' : ''} creada{result.created !== 1 ? 's' : ''}
              </p>
              {result.skipped > 0 && (
                <p className="text-sm text-green-600">{result.skipped} activo{result.skipped !== 1 ? 's' : ''} omitido{result.skipped !== 1 ? 's' : ''} (ya tenían OT activa)</p>
              )}
              {result.warnings?.map((w, i) => (
                <p key={i} className="text-xs text-yellow-600 flex items-center gap-1">
                  <Icon name="warning" className="w-3.5 h-3.5 flex-shrink-0" />
                  {w}
                </p>
              ))}
            </div>
            <div className="flex justify-end">
              <button onClick={onClose} className="px-5 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light">
                Cerrar
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
