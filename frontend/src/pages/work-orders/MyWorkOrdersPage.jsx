import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useOfflineWorkOrders,
  useWorkOrdersWithPendingSync,
} from '../../hooks/useOfflineWorkOrders'
import StatusBadge from '../../components/workOrders/StatusBadge'
import PriorityBadge from '../../components/workOrders/PriorityBadge'
import TransitionButton from '../../components/workOrders/TransitionButton'
import Icon from '../../components/ui/Icon'
import { taskTypeLabel } from '../../constants/labels'
import Spinner from '../../components/ui/Spinner'
import { formatWoCode } from '../../utils/workOrder'

const TABS = [
  { label: 'Pendientes',   filter: 'PENDING' },
  { label: 'En proceso',   filter: 'IN_PROGRESS' },
  { label: 'En revisión',  filter: 'IN_REVIEW' },
  { label: 'Todas',        filter: '' },
]


export default function MyWorkOrdersPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState(0)

  const statusFilter = TABS[activeTab].filter
  const { data: workOrders = [], isLoading, refetch } = useOfflineWorkOrders(
    statusFilter ? { status: statusFilter } : {}
  )
  const pendingSyncIds = useWorkOrdersWithPendingSync()

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Mis órdenes de trabajo</h1>
        <p className="text-sm text-gray-500 mt-0.5">Órdenes asignadas a ti</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
        {TABS.map((tab, i) => (
          <button
            key={tab.filter}
            onClick={() => setActiveTab(i)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === i
                ? 'bg-white text-brand shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Cards */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : workOrders.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <Icon name="wrench" className="w-10 h-10 mx-auto mb-3 text-gray-400" />
          <p className="font-medium">No hay órdenes en esta categoría</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {workOrders.map((wo) => (
            <WorkOrderCard
              key={wo.id}
              wo={wo}
              onTransition={refetch}
              navigate={navigate}
              hasPendingSync={pendingSyncIds.has(wo.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function WorkOrderCard({ wo, onTransition, navigate, hasPendingSync = false }) {
  const isOverdue = wo.is_overdue

  return (
    <div className={`relative bg-white rounded-xl border shadow-sm p-4 space-y-3 ${
      isOverdue ? 'border-red-200' : 'border-gray-100'
    }`}>
      {/* Evidencia guardada sin conexion, aun no subida al servidor */}
      {hasPendingSync && (
        <span
          className="absolute top-2 right-2 flex h-2.5 w-2.5"
          title="Datos pendientes de sincronizar"
        >
          <span className="absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-60 motion-safe:animate-ping" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-amber-500" />
          <span className="sr-only">Datos pendientes de sincronizar</span>
        </span>
      )}

      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="font-mono text-xs text-gray-500 font-semibold">{formatWoCode(wo)}</span>
          <span className="ml-2 text-xs px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">
            {taskTypeLabel(wo.task_type)}
          </span>
        </div>
        <PriorityBadge priority={wo.priority} />
      </div>

      {/* Título */}
      <p className="font-medium text-gray-800 text-sm leading-snug line-clamp-2">{wo.title}</p>

      {/* Activo y hospital */}
      <div className="text-xs text-gray-500 space-y-0.5">
        <p><span className="font-mono">{wo.asset?.code}</span> — {wo.asset?.name}</p>
        <p className="text-gray-500">{wo.hospital?.name}</p>
      </div>

      {/* Status */}
      <div className="flex items-center gap-2">
        <StatusBadge status={wo.status} />
      </div>

      {/* Fecha límite */}
      <p className={`text-xs font-medium flex items-center gap-1 ${isOverdue ? 'text-red-600' : 'text-gray-500'}`}>
        {isOverdue && <Icon name="warning" className="w-3.5 h-3.5 flex-shrink-0" />}
        {isOverdue ? 'Vencida — ' : 'Límite: '}
        {wo.scheduled_date}
      </p>

      {/* Acciones */}
      <div className="pt-1 flex flex-col gap-2">
        <TransitionButton workOrder={wo} onSuccess={onTransition} />
        <button
          onClick={() => navigate(`/mis-ordenes/${wo.id}`)}
          className="w-full inline-flex items-center justify-center gap-1 text-sm py-1.5 border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Ver detalle
          <Icon name="chevronRight" className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
