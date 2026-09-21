import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import { useMaintenancePlans, usePausePlan, useResumePlan } from '../../api/maintenance'
import Icon from '../../components/ui/Icon'
import Spinner from '../../components/ui/Spinner'
import { taskTypeLabel } from '../../constants/labels'
import { formatDate, formatFrequency, relativeDue } from '../../utils/maintenance'

function ComplianceBar({ pct }) {
  if (pct === null || pct === undefined) {
    return <span className="text-xs text-gray-500">Sin datos</span>
  }
  const color = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-400' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 bg-gray-100 rounded-full overflow-hidden">
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
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')

  const params = {
    ...(statusFilter && { is_active: statusFilter === 'active' }),
    ...(search && { search }),
  }
  const { data: plans = [], isLoading, isError } = useMaintenancePlans(params)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Planes de tareas</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Cada activo tiene un plan; el plan dice qué tareas se le hacen y cada cuánto.
          </p>
        </div>
        {isAdmin && (
          <button onClick={() => navigate('/planes-pm/nuevo')}
            className="px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light transition-colors flex items-center gap-1.5">
            <Icon name="plus" className="w-4 h-4" />
            Nuevo plan
          </button>
        )}
      </div>

      <div className="flex gap-2 flex-wrap items-center">
        {[
          { value: '', label: 'Todos' },
          { value: 'active', label: 'Activos' },
          { value: 'inactive', label: 'Pausados' },
        ].map(({ value, label }) => (
          <button key={value} onClick={() => setStatusFilter(value)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              statusFilter === value
                ? 'bg-brand text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}>
            {label}
          </button>
        ))}
        <form onSubmit={(e) => { e.preventDefault(); setSearch(searchInput.trim()) }}
          className="flex items-center gap-2 ml-auto">
          <input value={searchInput} onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Buscar plan por nombre" aria-label="Buscar plan por nombre"
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm w-56 focus:outline-none focus:ring-2 focus:ring-brand/30" />
          <button type="submit" className="px-3 py-1.5 text-sm rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50">
            Buscar
          </button>
        </form>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        {isError ? (
          <div className="text-center py-16 text-red-600 text-sm">
            No se pudieron cargar los planes de tareas. Revisa tu conexión e intenta de nuevo.
          </div>
        ) : isLoading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : plans.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <Icon name="plan" className="w-10 h-10 mx-auto mb-3 text-gray-400" />
            <p className="font-medium">{search ? `Ningún plan coincide con «${search}»` : 'No hay planes de tareas'}</p>
            {isAdmin && !search && (
              <button onClick={() => navigate('/planes-pm/nuevo')} className="mt-3 text-sm text-brand hover:underline">
                Crear el primer plan
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr className="text-left text-xs font-medium text-gray-500">
                  <th className="px-4 py-3">Plan</th>
                  <th className="px-4 py-3">Tareas</th>
                  <th className="px-4 py-3">Activos</th>
                  <th className="px-4 py-3">Próxima fecha</th>
                  <th className="px-4 py-3">Cumplimiento del mes</th>
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {plans.map((plan) => (
                  <PlanRow key={plan.id} plan={plan} isAdmin={isAdmin}
                    onView={() => navigate(`/planes-pm/${plan.id}`)}
                    onEdit={() => navigate(`/planes-pm/${plan.id}/editar`)} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function PlanRow({ plan, isAdmin, onView, onEdit }) {
  const pauseMut = usePausePlan(plan.id)
  const resumeMut = useResumePlan(plan.id)
  const activas = plan.tasks.filter((t) => t.is_active)

  return (
    <tr className="hover:bg-gray-50 transition-colors align-top">
      <td className="px-4 py-3">
        <button onClick={onView} className="font-medium text-gray-800 hover:text-brand text-left">{plan.name}</button>
        {plan.description && <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{plan.description}</p>}
      </td>
      <td className="px-4 py-3">
        {activas.length === 0 ? (
          <span className="text-xs text-amber-700">Sin tareas: no genera nada</span>
        ) : (
          <ul className="space-y-0.5">
            {activas.slice(0, 2).map((t) => (
              <li key={t.id} className="text-xs text-gray-600">
                <span className="text-gray-800">{t.name}</span>
                <span className="text-gray-500"> · {taskTypeLabel(t.task_type)} · {formatFrequency(t)}</span>
              </li>
            ))}
            {activas.length > 2 && <li className="text-xs text-gray-500">y {activas.length - 2} más</li>}
          </ul>
        )}
      </td>
      <td className="px-4 py-3 text-gray-600">{plan.assets_count}</td>
      <td className="px-4 py-3 whitespace-nowrap">
        {plan.next_due_date ? (
          <>
            <p className="text-gray-700 whitespace-nowrap">{formatDate(plan.next_due_date)}</p>
            <p className="text-xs text-gray-500">{relativeDue(plan.next_due_date)}</p>
          </>
        ) : <span className="text-gray-500">—</span>}
        {plan.overdue_count > 0 && (
          <span className="inline-block mt-1 text-xs px-1.5 py-0.5 rounded bg-red-50 text-red-700">
            {plan.overdue_count} vencida{plan.overdue_count !== 1 ? 's' : ''}
          </span>
        )}
      </td>
      <td className="px-4 py-3"><ComplianceBar pct={plan.compliance_percentage} /></td>
      <td className="px-4 py-3">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          plan.is_active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
        }`}>
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
                <button onClick={() => pauseMut.mutate()} disabled={pauseMut.isPending}
                  className="text-xs px-2 py-1 rounded bg-yellow-50 text-yellow-700 hover:bg-yellow-100 disabled:opacity-50">
                  Pausar
                </button>
              ) : (
                <button onClick={() => resumeMut.mutate()} disabled={resumeMut.isPending}
                  className="text-xs px-2 py-1 rounded bg-green-50 text-green-700 hover:bg-green-100 disabled:opacity-50">
                  Reanudar
                </button>
              )}
            </>
          )}
        </div>
      </td>
    </tr>
  )
}
