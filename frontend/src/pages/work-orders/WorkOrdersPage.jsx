import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import { useWorkOrders } from '../../api/workOrders'
import StatusBadge from '../../components/workOrders/StatusBadge'
import PriorityBadge from '../../components/workOrders/PriorityBadge'
import Icon from '../../components/ui/Icon'
import { taskTypeLabel } from '../../constants/labels'
import Spinner from '../../components/ui/Spinner'
import { formatWoCode } from '../../utils/workOrder'

const PAGE_SIZE = 20


export default function WorkOrdersPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'ADMIN'

  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [isOverdue, setIsOverdue] = useState(false)
  const [page, setPage] = useState(1)

  const params = {
    ...(statusFilter && { status: statusFilter }),
    ...(priorityFilter && { priority: priorityFilter }),
    ...(typeFilter && { task_type: typeFilter }),
    ...(search && { search }),
    ...(isOverdue && { is_overdue: true }),
  }

  const { data: workOrders = [], isLoading, isError } = useWorkOrders(params)

  const totalPages = Math.max(1, Math.ceil(workOrders.length / PAGE_SIZE))
  const paginated = workOrders.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  function handleSearch(e) {
    e.preventDefault()
    setSearch(searchInput)
    setPage(1)
  }

  function handleFilterChange(setter) {
    return (e) => { setter(e.target.value); setPage(1) }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Órdenes de trabajo</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {workOrders.length} {workOrders.length === 1 ? 'orden' : 'órdenes'} encontradas
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => navigate('/ordenes/nueva')}
            className="px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light transition-colors"
          >
            + Nueva OT
          </button>
        )}
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-card p-4">
        <div className="flex flex-wrap gap-3 items-center">
          <form onSubmit={handleSearch} className="flex gap-1">
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Título, N° OT, activo..."
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 w-48"
            />
            <button type="submit" className="px-3 py-1.5 bg-brand text-white text-sm rounded-lg hover:bg-brand-light">
              Buscar
            </button>
            {search && (
              <button type="button" onClick={() => { setSearch(''); setSearchInput(''); setPage(1) }}
                className="px-2 py-1.5 text-gray-500 hover:text-gray-600" aria-label="Limpiar busqueda"><Icon name="close" className="w-4 h-4" /></button>
            )}
          </form>

          <select value={statusFilter} onChange={handleFilterChange(setStatusFilter)}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none">
            <option value="">Todos los estados</option>
            <option value="PENDING">Pendiente</option>
            <option value="IN_PROGRESS">En proceso</option>
            <option value="IN_REVIEW">En revisión</option>
            <option value="COMPLETED">Finalizada</option>
            <option value="CANCELLED">Cancelada</option>
          </select>

          <select value={priorityFilter} onChange={handleFilterChange(setPriorityFilter)}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none">
            <option value="">Todas las prioridades</option>
            <option value="HIGH">Alta</option>
            <option value="MEDIUM">Media</option>
            <option value="LOW">Baja</option>
          </select>

          <select value={typeFilter} onChange={handleFilterChange(setTypeFilter)}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none">
            <option value="">Todos los tipos</option>
            <option value="CORRECTIVE">Correctivo</option>
            <option value="PREVENTIVE">Preventivo</option>
            <option value="VERIFICATION">Verificación</option>
            <option value="INSTALLATION">Instalación</option>
            <option value="DELIVERY">Entrega</option>
          </select>

          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={isOverdue}
              onChange={(e) => { setIsOverdue(e.target.checked); setPage(1) }}
              className="rounded border-gray-300 text-brand focus:ring-brand"
            />
            Solo vencidas
          </label>
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : isError ? (
          <div className="text-center py-16 text-red-600 text-sm">
            No se pudo cargar las órdenes de trabajo. Revisa tu conexión e intenta de nuevo.
          </div>
        ) : workOrders.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <Icon name="wrench" className="w-10 h-10 mx-auto mb-3 text-gray-400" />
            <p className="font-medium">No hay órdenes de trabajo</p>
            {isAdmin && (
              <button onClick={() => navigate('/ordenes/nueva')}
                className="mt-3 text-sm text-brand hover:underline">
                + Crear la primera OT
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr className="text-left text-xs font-medium text-gray-500">
                    <th className="px-4 py-3">N° OT</th>
                    <th className="px-4 py-3">Tipo</th>
                    <th className="px-4 py-3">Título</th>
                    <th className="px-4 py-3">Activo</th>
                    <th className="px-4 py-3">Hospital</th>
                    <th className="px-4 py-3">Prioridad</th>
                    <th className="px-4 py-3">Estado</th>
                    <th className="px-4 py-3">Técnico</th>
                    <th className="px-4 py-3">F. Límite</th>
                    <th className="px-4 py-3">PDF</th>
                    <th className="px-4 py-3 text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {paginated.map((wo) => (
                    <tr
                      key={wo.id}
                      className={`hover:bg-gray-50 transition-colors cursor-pointer ${wo.is_overdue ? 'bg-red-50 hover:bg-red-100' : ''}`}
                      onClick={() => navigate(`/ordenes/${wo.id}`)}
                    >
                      <td className="px-4 py-3 font-mono text-xs text-gray-500 font-semibold">
                        {formatWoCode(wo)}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {taskTypeLabel(wo.task_type)}
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-800 max-w-[200px] truncate">
                        {wo.title}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        <div className="font-mono">{wo.asset?.code}</div>
                        <div className="truncate max-w-[120px]">{wo.asset?.name}</div>
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs truncate max-w-[100px]">
                        {wo.hospital?.name}
                      </td>
                      <td className="px-4 py-3">
                        <PriorityBadge priority={wo.priority} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={wo.status} />
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs truncate max-w-[100px]">
                        {wo.assigned_to?.full_name ?? '—'}
                      </td>
                      <td className={`px-4 py-3 text-xs ${wo.is_overdue ? 'text-red-600 font-semibold' : 'text-gray-500'}`}>
                        {wo.scheduled_date}
                        {wo.is_overdue && <Icon name="warning" className="w-3.5 h-3.5 inline-block ml-1 align-text-bottom" />}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {wo.has_report === true && (
                          <Icon name="report" title="Reporte disponible" className="w-4 h-4 mx-auto text-green-600" />
                        )}
                        {wo.has_report === false && (
                          <Icon name="clock" title="Generando reporte..." className="w-4 h-4 mx-auto text-gray-400" />
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={(e) => { e.stopPropagation(); navigate(`/ordenes/${wo.id}`) }}
                          className="text-xs px-2 py-1 rounded bg-brand/10 text-brand hover:bg-brand/20"
                        >
                          Ver
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Paginación */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
                <span className="text-xs text-gray-500">
                  Página {page} de {totalPages} ({workOrders.length} resultados)
                </span>
                <div className="flex gap-1">
                  <button disabled={page === 1} onClick={() => setPage((p) => p - 1)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50">
                    <Icon name="chevronLeft" className="w-3.5 h-3.5" />
                    Anterior
                  </button>
                  <button disabled={page === totalPages} onClick={() => setPage((p) => p + 1)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50">
                    Siguiente
                    <Icon name="chevronRight" className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
