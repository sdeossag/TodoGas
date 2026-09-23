import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import {
  useWorkOrder,
  useWorkOrderHistory,
  useUpdateWorkOrder,
  useSetTaskChecklist,
  useAssignWorkOrder,
  useAddWorkOrderTasks,
  useRemoveWorkOrderTask,
} from '../../api/workOrders'
import { useTasks } from '../../api/tasks'
import Modal from '../../components/ui/Modal'
import { formatDate } from '../../utils/maintenance'
import { useUsers } from '../../api/users'
import { formatWoCode } from '../../utils/workOrder'
import {
  useChecklistResponse,
  useChecklistTemplates,
  useCreateChecklistResponse,
  useSubmitField,
  useCompleteChecklist,
  useSetBlockCount,
} from '../../api/checklists'
import { getFieldType } from '../../constants/checklistFields'
import StatusBadge from '../../components/workOrders/StatusBadge'
import PriorityBadge from '../../components/workOrders/PriorityBadge'
import TransitionButton from '../../components/workOrders/TransitionButton'
import SignatureList from '../../components/evidence/SignatureList'
import SignaturePad from '../../components/evidence/SignaturePad'
import PhotoGallery from '../../components/evidence/PhotoGallery'
import PhotoCapture, { dataUrlToFile } from '../../components/evidence/PhotoCapture'
import { useUploadPhoto, useWorkOrderPhotos } from '../../api/evidence'
import { mediaUrl } from '../../api/client'
import { Capacitor } from '@capacitor/core'
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera'
import {
  REPORT_POLL_ATTEMPTS,
  useWorkOrderReports,
  useReportDownload,
  useRegenerateReport,
  useResendReportEmail,
} from '../../api/reports'
import { useInventoryItems, useStockMovements, useCreateStockMovement } from '../../api/inventory'
import { useIntegrityCheck } from '../../api/dashboard'
import Icon from '../../components/ui/Icon'
import { taskTypeLabel, woStatusLabel } from '../../constants/labels'
import useModalDismiss from '../../hooks/useModalDismiss'
import useNetworkStore from '../../store/networkStore'
import {
  markChecklistCompletedOffline,
  markFieldResponseSynced,
  newId,
  saveChecklistResponse,
  saveFieldResponse,
  savePhotoOffline,
  setBlockCountOffline,
} from '../../db/repositories'
import { countFor, isRepeatable, slotKey, slots } from '../../utils/checklistSlots'

// Margen sobre la ventana de sondeo de useWorkOrderReports (24 intentos x 5s).
const REPORT_POLL_TIMEOUT_MS = REPORT_POLL_ATTEMPTS * 5000

const STATUS_DOTS = {
  PENDING: 'bg-gray-400',
  IN_PROGRESS: 'bg-blue-500',
  IN_REVIEW: 'bg-amber-500',
  COMPLETED: 'bg-green-600',
  CANCELLED: 'bg-red-500',
}

function Spinner({ small }) {
  return (
    <svg className={`animate-spin ${small ? 'h-4 w-4' : 'h-8 w-8'} text-brand`} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

function formatDuration(d) {
  if (!d) return '—'
  const parts = d.split(', ')
  const timePart = parts[parts.length - 1]
  const [h, m] = timePart.split(':')
  const days = parts.length > 1 ? parseInt(parts[0]) : 0
  const totalHours = days * 24 + parseInt(h || 0)
  return `${totalHours}h ${parseInt(m || 0)}m`
}

function InfoRow({ label, value }) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-500 mb-0.5">{label}</dt>
      <dd className="text-sm text-gray-800">{value ?? '—'}</dd>
    </div>
  )
}

export default function WorkOrderDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const role = user?.role
  const isAdmin = role === 'ADMIN'
  const isAdminOrSup = ['ADMIN', 'SUP'].includes(role)

  const [tab, setTab] = useState(role === 'TEC' ? 1 : 0)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showAssignModal, setShowAssignModal] = useState(false)

  const { data: wo, isLoading, isError, error, refetch } = useWorkOrder(id)

  // Determine back route by role
  const backPath = role === 'TEC' ? '/mis-ordenes' : '/ordenes'

  if (isLoading) return <div className="flex justify-center py-20"><Spinner /></div>
  if (isError || !wo) {
    return (
      <div className="text-center py-20 text-gray-500">
        <Icon name="warning" className="w-10 h-10 mx-auto mb-3 text-amber-500" />
        <p>{error?.message && !error?.response ? error.message : 'No se encontró la OT'}</p>
        <button onClick={() => navigate(backPath)} className="mt-3 text-sm text-brand hover:underline">
          Volver
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 flex gap-1">
        <button onClick={() => navigate(backPath)} className="hover:text-brand">
          {role === 'TEC' ? 'Mis órdenes' : 'Órdenes de trabajo'}
        </button>
        <span>/</span>
        <span className="text-gray-600">{formatWoCode(wo)}</span>
      </nav>

      {/* Encabezado */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-card p-6 space-y-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <span className="font-mono text-sm font-bold text-gray-500">{formatWoCode(wo)}</span>
              <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded">
                {taskTypeLabel(wo.task_type)}
              </span>
              <StatusBadge status={wo.status} />
              <PriorityBadge priority={wo.priority} />
            </div>
            <h1 className="text-xl font-bold text-gray-800">{wo.title}</h1>
          </div>
          <div className="flex gap-2 flex-wrap">
            {isAdminOrSup && (
              <button
                onClick={() => setShowEditModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50"
              >
                <Icon name="edit" className="w-4 h-4" />
                Editar
              </button>
            )}
          </div>
        </div>

        {/* Botones de transición */}
        <TransitionButton workOrder={wo} onSuccess={refetch} />
      </div>

      {/* Grid de información */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Activo y hospital */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-card p-5 space-y-4">
          {(wo.tasks?.length ?? 0) > 1 ? (
            <>
              <h2 className="font-semibold text-gray-800 text-sm">Activos</h2>
              <dl className="grid grid-cols-2 gap-4">
                <InfoRow label="Hospital" value={wo.hospital?.name} />
                <InfoRow label="Ubicación" value={wo.location?.path} />
                <InfoRow label="Activos" value={`${wo.tasks.length} — ver la pestaña Tareas`} />
              </dl>
            </>
          ) : (
            <>
              <h2 className="font-semibold text-gray-800 text-sm">Activo</h2>
              <dl className="grid grid-cols-2 gap-4">
                <InfoRow label="Código" value={<span className="font-mono">{wo.assets?.[0]?.code}</span>} />
                <InfoRow label="Nombre" value={wo.assets?.[0]?.name} />
                <InfoRow label="Hospital" value={wo.hospital?.name} />
                {wo.location && <InfoRow label="Ubicación" value={wo.location.path} />}
              </dl>
            </>
          )}
        </div>

        {/* Asignación */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-card p-5 space-y-4">
          <h2 className="font-semibold text-gray-800 text-sm">Asignación</h2>
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-xs font-medium text-gray-500 mb-0.5">Técnico asignado</dt>
              <dd className="text-sm text-gray-800 flex items-center gap-2">
                {wo.assigned_to?.full_name ?? '—'}
                {isAdmin && (
                  <button
                    onClick={() => setShowAssignModal(true)}
                    className="text-xs text-brand hover:underline"
                  >
                    Reasignar
                  </button>
                )}
              </dd>
            </div>
            <InfoRow label="Creado por" value={wo.created_by?.full_name} />
          </dl>
        </div>

        {/* Fechas y duraciones */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-card p-5 space-y-4">
          <h2 className="font-semibold text-gray-800 text-sm">Fechas</h2>
          <dl className="grid grid-cols-2 gap-4">
            <InfoRow label="Fecha programada" value={wo.scheduled_date} />
            <InfoRow label="Inicio real" value={wo.started_at ? new Date(wo.started_at).toLocaleString('es-CO') : null} />
            <InfoRow label="Cierre" value={wo.completed_at ? new Date(wo.completed_at).toLocaleString('es-CO') : null} />
            <InfoRow label="Dur. estimada" value={formatDuration(wo.estimated_duration)} />
            <InfoRow label="Dur. real" value={formatDuration(wo.actual_duration)} />
          </dl>
        </div>

        {/* Progreso y costos */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-card p-5 space-y-4">
          <h2 className="font-semibold text-gray-800 text-sm">Progreso</h2>
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-gray-500">Avance</span>
              <span className="text-sm font-semibold text-gray-700">{wo.progress ?? 0}%</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div
                className="bg-brand rounded-full h-2 transition-all"
                style={{ width: `${wo.progress ?? 0}%` }}
              />
            </div>
          </div>
          <dl className="grid grid-cols-2 gap-4 pt-2">
            <InfoRow label="Costo total" value={wo.total_cost ? `$${parseFloat(wo.total_cost).toLocaleString('es-CO')}` : null} />
            <InfoRow
              label="Calificación"
              value={
                wo.rating ? (
                  <span className="inline-flex items-center gap-0.5">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <Icon
                        key={n}
                        name="star"
                        className={`w-4 h-4 ${n <= wo.rating ? 'text-amber-500' : 'text-gray-300'}`}
                      />
                    ))}
                    <span className="ml-1.5 text-gray-500">({wo.rating}/5)</span>
                  </span>
                ) : null
              }
            />
            {wo.tasks?.length === 1 && wo.tasks[0].plan && (
              <InfoRow label="Plan de tareas" value={wo.tasks[0].plan.name} />
            )}
          </dl>
        </div>
      </div>

      {/* Notas */}
      {wo.notes && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
          <h2 className="font-semibold text-gray-800 text-sm mb-2">Notas</h2>
          <p className="text-sm text-gray-600 whitespace-pre-line">{wo.notes}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        <div className="border-b border-gray-100">
          <div className="flex overflow-x-auto">
            {[
              'Historial de estados',
              (wo.tasks?.length ?? 0) > 1 ? `Tareas (${wo.tasks.length})` : 'Checklist',
              'Evidencia',
              'Repuestos',
              'Reportes',
            ].map((label, i) => (
              <button
                key={label}
                onClick={() => setTab(i)}
                className={`flex-shrink-0 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                  tab === i
                    ? 'border-brand text-brand'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="p-6">
          {tab === 0 && <HistoryTab id={id} isAdminOrSup={isAdminOrSup} />}
          {tab === 1 && <TasksTab wo={wo} user={user} refetch={refetch} />}
          {tab === 3 && <RepuestosTab wo={wo} user={user} />}
          {tab === 4 && (
            <ReportsTab
              workOrderId={id}
              woStatus={wo.status}
              reportStatus={wo.report_status}
              role={role}
            />
          )}
          {tab === 2 && (
            <div className="space-y-8">
              <div>
                <h3 className="text-xs font-semibold text-gray-500 border-b border-gray-200 pb-2 mb-4">
                  Firmas
                </h3>
                <SignatureList workOrderId={id} />
              </div>
              {['ADMIN', 'TEC'].includes(role) && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-500 border-b border-gray-200 pb-2 mb-4">
                    Agregar firma
                  </h3>
                  <SignaturePad workOrderId={id} disabled={wo.status !== 'IN_PROGRESS'} />
                </div>
              )}
              <div>
                <h3 className="text-xs font-semibold text-gray-500 border-b border-gray-200 pb-2 mb-4">
                  Fotos
                </h3>
                <PhotoGallery workOrderId={id} />
              </div>
              {['ADMIN', 'TEC'].includes(role) && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-500 border-b border-gray-200 pb-2 mb-4">
                    Agregar foto
                  </h3>
                  <PhotoCapture workOrderId={id} tasks={wo.tasks ?? []} disabled={wo.status !== 'IN_PROGRESS'} />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Modal de edición */}
      {showEditModal && (
        <EditModal wo={wo} onClose={() => setShowEditModal(false)} onSuccess={refetch} />
      )}

      {/* Modal de reasignación */}
      {showAssignModal && (
        <AssignModal woId={wo.id} onClose={() => setShowAssignModal(false)} onSuccess={refetch} />
      )}
    </div>
  )
}

// ── Historial tab ────────────────────────────────────────────────────────────

function HistoryTab({ id, isAdminOrSup }) {
  const { data: history = [], isLoading, isError } = useWorkOrderHistory(id, isAdminOrSup)

  if (!isAdminOrSup) {
    return <p className="text-gray-500 text-sm text-center py-6">No disponible para tu rol</p>
  }
  if (isLoading) return <div className="flex justify-center py-6"><Spinner small /></div>
  if (isError) return <p className="text-red-400 text-sm text-center py-6">Error al cargar el historial</p>
  if (history.length === 0) return <p className="text-gray-500 text-sm text-center py-6">Sin cambios de estado aún</p>

  return (
    <ol className="relative border-l border-gray-200 space-y-6 pl-6">
      {history.map((entry) => (
        <li key={entry.id} className="relative">
          <span className="absolute -left-[1.65rem] flex items-center justify-center w-8 h-8">
            <span
              className={`w-2.5 h-2.5 rounded-full ring-4 ring-white ${
                STATUS_DOTS[entry.to_status] ?? 'bg-gray-300'
              }`}
            />
          </span>
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className="text-xs text-gray-500">
                {new Date(entry.changed_at).toLocaleString('es-CO')}
              </span>
              <span className="text-xs text-gray-500">·</span>
              <span className="text-xs font-medium text-gray-600">{entry.changed_by?.full_name}</span>
            </div>
            <p className="text-sm text-gray-700">
              {entry.from_status
                ? <><span className="text-gray-500">{woStatusLabel(entry.from_status)}</span> → <strong>{woStatusLabel(entry.to_status)}</strong></>
                : <><strong>{woStatusLabel(entry.to_status)}</strong> (estado inicial)</>
              }
            </p>
            {entry.comment && (
              <p className="mt-1 text-xs text-gray-500 italic">"{entry.comment}"</p>
            )}
          </div>
        </li>
      ))}
    </ol>
  )
}

// ── Modal de reasignación ────────────────────────────────────────────────────

function AssignModal({ woId, onClose, onSuccess }) {
  useModalDismiss(onClose)
  const [selectedTec, setSelectedTec] = useState('')
  const { data: _allUsers = [], isLoading } = useUsers({})
  const tecUsers = _allUsers.filter((u) => u.role === 'TEC' && u.is_active)
  const assignMut = useAssignWorkOrder(woId)

  async function handleAssign() {
    if (!selectedTec) return
    await assignMut.mutateAsync({ assigned_to: selectedTec })
    onSuccess?.()
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-[2px]">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
        <div className="flex items-start justify-between gap-4 mb-4">
          <h3 className="text-lg font-semibold text-gray-800">Reasignar técnico</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="p-1 -mr-1 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <Icon name="close" className="w-5 h-5" />
          </button>
        </div>
        {isLoading ? (
          <div className="flex justify-center py-4"><Spinner small /></div>
        ) : (
          <select
            value={selectedTec}
            onChange={(e) => setSelectedTec(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 mb-4"
          >
            <option value="">Seleccionar técnico...</option>
            {tecUsers.map((u) => (
              <option key={u.id} value={u.id}>
                {u.first_name} {u.last_name}
              </option>
            ))}
          </select>
        )}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
            Cancelar
          </button>
          <button
            onClick={handleAssign}
            disabled={!selectedTec || assignMut.isPending}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60"
          >
            {assignMut.isPending && <Spinner small />}
            Reasignar
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Modal de edición ─────────────────────────────────────────────────────────

function EditModal({ wo, onClose, onSuccess }) {
  useModalDismiss(onClose)
  const { data: _editUsers = [] } = useUsers({})
  const tecUsers = _editUsers.filter((u) => u.role === 'TEC' && u.is_active)
  const updateMut = useUpdateWorkOrder(wo.id)
  const taskChecklistMut = useSetTaskChecklist(wo.id)

  // Una vez respondido el checklist la version queda fija: cambiarla dejaria
  // las respuestas apuntando a campos de otra version. Desde la fase 3 el
  // checklist existe desde que la tarea entra en la OT, asi que lo que cuenta
  // es si ya tiene respuestas. Con varias tareas cada una tiene el suyo.
  const primera = wo.tasks?.[0]
  const variasTareas = (wo.tasks?.length ?? 0) > 1
  const checklistLocked =
    variasTareas || !!primera?.checklist?.completed_at || (primera?.checklist?.answered ?? 0) > 0
  const { data: checklistTemplates = [] } = useChecklistTemplates({ is_active: true })
  const publishedChecklists = checklistTemplates.filter((t) => t.current_version_id)

  const [form, setForm] = useState({
    title: wo.title ?? '',
    description: wo.description ?? '',
    priority: wo.priority ?? 'MEDIUM',
    scheduled_date: wo.scheduled_date ?? '',
    estimated_duration: wo.estimated_duration ? wo.estimated_duration.substring(0, 5) : '',
    assigned_to: wo.assigned_to?.id ?? '',
    checklist_version: wo.tasks?.[0]?.checklist_version?.id ?? '',
    notes: wo.notes ?? '',
    classification_1: wo.classification_1 ?? '',
    classification_2: wo.classification_2 ?? '',
  })

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  async function handleSave() {
    const payload = {
      title: form.title,
      description: form.description,
      priority: form.priority,
      scheduled_date: form.scheduled_date,
      notes: form.notes,
      classification_1: form.classification_1,
      classification_2: form.classification_2,
      ...(form.estimated_duration && { estimated_duration: form.estimated_duration + ':00' }),
      ...(form.assigned_to && { assigned_to: form.assigned_to }),
    }
    await updateMut.mutateAsync(payload)
    // El checklist es de la tarea: va por su propia ruta.
    const versionActual = primera?.checklist_version?.id ?? ''
    if (!checklistLocked && primera && form.checklist_version !== versionActual) {
      await taskChecklistMut.mutateAsync({
        task: primera.id,
        checklist_version: form.checklist_version || null,
      })
    }
    onSuccess?.()
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-[2px]">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between gap-4 mb-4">
          <h3 className="text-lg font-semibold text-gray-800">Editar OT</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="p-1 -mr-1 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <Icon name="close" className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          <Field label="Título *">
            <input value={form.title} onChange={(e) => set('title', e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30" />
          </Field>

          <Field label="Descripción">
            <textarea rows={3} value={form.description} onChange={(e) => set('description', e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 resize-none" />
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Prioridad">
              <select value={form.priority} onChange={(e) => set('priority', e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30">
                <option value="HIGH">Alta</option>
                <option value="MEDIUM">Media</option>
                <option value="LOW">Baja</option>
              </select>
            </Field>
            <Field label="Fecha límite">
              <input type="date" value={form.scheduled_date} onChange={(e) => set('scheduled_date', e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30" />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Dur. estimada (HH:MM)">
              <input value={form.estimated_duration} onChange={(e) => set('estimated_duration', e.target.value)}
                placeholder="02:30" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30" />
            </Field>
            <Field label="Técnico asignado">
              <select value={form.assigned_to} onChange={(e) => set('assigned_to', e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30">
                <option value="">Sin asignar</option>
                {tecUsers.map((u) => (
                  <option key={u.id} value={u.id}>{u.first_name} {u.last_name}</option>
                ))}
              </select>
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Clasificación 1">
              <input value={form.classification_1} onChange={(e) => set('classification_1', e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30" />
            </Field>
            <Field label="Clasificación 2">
              <input value={form.classification_2} onChange={(e) => set('classification_2', e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30" />
            </Field>
          </div>

          <Field label="Checklist">
            <select
              value={form.checklist_version}
              onChange={(e) => set('checklist_version', e.target.value)}
              disabled={checklistLocked}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 disabled:bg-gray-50 disabled:text-gray-500"
            >
              <option value="">Sin checklist</option>
              {publishedChecklists.map((t) => (
                <option key={t.id} value={t.current_version_id}>
                  {t.name} (v{t.current_version_number})
                </option>
              ))}
            </select>
            {checklistLocked && (
              <p className="text-xs text-gray-500 mt-1">
                {variasTareas
                  ? 'La OT tiene varias tareas: cada una lleva el checklist de su plan.'
                  : 'El checklist ya tiene respuestas y no se puede cambiar.'}
              </p>
            )}
          </Field>

          <Field label="Notas">
            <textarea rows={2} value={form.notes} onChange={(e) => set('notes', e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 resize-none" />
          </Field>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={!form.title.trim() || updateMut.isPending}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60"
          >
            {updateMut.isPending && <Spinner small />}
            Guardar cambios
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  )
}

// ── Checklist tab ─────────────────────────────────────────────────────────────

// ── Tareas y checklists ──────────────────────────────────────────────────────

/**
 * Las tareas de la OT, una por activo, cada una con su checklist. Con una sola
 * tarea se ve directamente su checklist, como antes; con varias, la lista con
 * el avance de cada activo, y al tocar una se abre su checklist debajo.
 */
function TasksTab({ wo, user, refetch }) {
  const visibles = (wo.tasks ?? []).filter(
    (t) => t.status !== 'CANCELLED' || wo.status === 'CANCELLED'
  )
  const [abierta, setAbierta] = useState(visibles.length === 1 ? visibles[0].id : null)
  const [agregando, setAgregando] = useState(false)
  const [quitando, setQuitando] = useState(null)
  const [preguntarRevision, setPreguntarRevision] = useState(false)

  const isTecAssigned = user?.role === 'TEC' && wo.assigned_to?.id === user?.id
  // Misma regla que firmas, fotos y repuestos: solo con la OT en curso.
  const isInProgress = wo.status === 'IN_PROGRESS'
  const canEdit = isTecAssigned && isInProgress
  const puedeAjustar = ['ADMIN', 'SUP'].includes(user?.role) && wo.status === 'PENDING'
  const varias = visibles.length > 1

  /**
   * Al cerrar un checklist se relee la OT; si con eso quedaron todos cerrados,
   * se pregunta si enviarla a revision, como Fracttal al llegar al 100 %.
   * Sugiere, no obliga.
   */
  async function alCerrarChecklist() {
    const { data } = await refetch()
    const conChecklist = (data?.tasks ?? []).filter((t) => t.status !== 'CANCELLED' && t.checklist_version)
    if (canEdit && conChecklist.length > 0 && conChecklist.every((t) => t.checklist?.completed_at)) {
      setPreguntarRevision(true)
    }
  }

  const aviso = isTecAssigned && !isInProgress && (
    <div className="mb-4 flex items-start gap-2 px-4 py-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
      <Icon name="warning" className="w-4 h-4 flex-shrink-0 mt-0.5" />
      <span>
        {wo.status === 'PENDING'
          ? 'Inicia la OT para responder los checklists y adjuntar fotos.'
          : 'Los checklists solo se pueden editar mientras la OT esta en proceso.'}
      </span>
    </div>
  )

  return (
    <div className="space-y-4">
      {aviso}

      {(varias || puedeAjustar) && (
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <p className="text-sm text-gray-600">
            {visibles.length} activo{visibles.length !== 1 ? 's' : ''}
            {wo.location && <span className="text-gray-500"> · {wo.location.path}</span>}
          </p>
          {puedeAjustar && (
            <button onClick={() => setAgregando(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50">
              <Icon name="plus" className="w-4 h-4" /> Agregar tareas
            </button>
          )}
        </div>
      )}

      {!varias && visibles[0] ? (
        <>
          {puedeAjustar && <TaskRow task={visibles[0]} abierta={false} onToggle={() => {}} />}
          {!puedeAjustar && visibles[0].checklist?.block_changes?.length > 0 && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              {visibles[0].checklist.block_changes.map((b) =>
                `${b.group}: el plan dice ${b.planned}, en campo se encontraron ${b.count}`
              ).join(' · ')}
              . Revisa el plan del activo.
            </p>
          )}
          <TaskChecklist wo={wo} task={visibles[0]} canEdit={canEdit} onChange={refetch} onComplete={alCerrarChecklist} />
        </>
      ) : (
        <ul className="space-y-2">
          {visibles.map((t) => (
            <li key={t.id} className="border border-gray-200 rounded-xl overflow-hidden">
              <TaskRow
                task={t}
                abierta={abierta === t.id}
                onToggle={() => setAbierta(abierta === t.id ? null : t.id)}
                onRemove={puedeAjustar ? () => setQuitando(t) : null}
              />
              {abierta === t.id && (
                <div className="border-t border-gray-100 p-4 bg-gray-50/40">
                  <TaskChecklist wo={wo} task={t} canEdit={canEdit} onChange={refetch} onComplete={alCerrarChecklist} />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {agregando && <AddTasksModal wo={wo} onClose={() => setAgregando(false)} onDone={refetch} />}
      {quitando && (
        <RemoveTaskModal wo={wo} task={quitando} onClose={() => setQuitando(null)} onDone={refetch} />
      )}
      {preguntarRevision && (
        <Modal title="Todos los checklists están completos" onClose={() => setPreguntarRevision(false)} width="max-w-md">
          <div className="space-y-4 text-sm text-gray-600">
            <p>¿Envías la OT a revisión? Si todavía te falta algo, puedes hacerlo más tarde desde arriba.</p>
            <TransitionButton workOrder={wo} onSuccess={() => { setPreguntarRevision(false); refetch() }} />
            <div className="flex justify-end">
              <button onClick={() => setPreguntarRevision(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
                Ahora no
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

function checklistState(task) {
  if (!task.checklist_version) return { label: 'Sin checklist', cls: 'bg-gray-100 text-gray-500' }
  const c = task.checklist
  if (c?.completed_at) return { label: 'Completo', cls: 'bg-green-50 text-green-700' }
  if (c?.answered > 0) return { label: 'En curso', cls: 'bg-blue-50 text-blue-700' }
  return { label: 'Sin empezar', cls: 'bg-gray-100 text-gray-600' }
}

function TaskRow({ task, abierta, onToggle, onRemove = null }) {
  const estado = checklistState(task)
  const c = task.checklist
  const pct = c?.total ? Math.round((c.answered / c.total) * 100) : 0
  return (
    <div className="flex items-stretch">
      <button type="button" onClick={onToggle} aria-expanded={abierta}
        className="flex-1 min-w-0 text-left px-4 py-3 hover:bg-gray-50 transition-colors">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-medium text-gray-800 truncate">
              <span className="font-mono text-xs text-gray-500">{task.asset.code}</span> {task.asset.name}
            </p>
            <p className="text-xs text-gray-500 truncate">
              {task.title}{task.plan && ` · ${task.plan.name}`}
              {task.asset.location && ` · ${task.asset.location}`}
            </p>
          </div>
          <span className={`flex-shrink-0 text-xs px-2 py-0.5 rounded-full ${estado.cls}`}>{estado.label}</span>
        </div>
        {c?.block_changes?.length > 0 && (
          <p className="mt-1.5 text-xs text-amber-700">
            {c.block_changes.map((b) =>
              `${b.group}: el plan dice ${b.planned}, en campo ${b.count}`
            ).join(' · ')}
          </p>
        )}
        {c && !c.completed_at && (
          <div className="mt-2 flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full bg-brand rounded-full" style={{ width: `${pct}%` }} />
            </div>
            <span className="text-xs text-gray-500 whitespace-nowrap">
              {c.answered} de {c.total}
              {c.required_missing > 0 && ` · ${c.required_missing} obligatorio${c.required_missing !== 1 ? 's' : ''}`}
            </span>
          </div>
        )}
      </button>
      {onRemove && (
        <button type="button" onClick={onRemove} aria-label={`Quitar ${task.asset.code} de la OT`}
          title="Quitar de la OT: vuelve a tareas pendientes"
          className="px-3 text-gray-400 hover:text-red-600 hover:bg-red-50 border-l border-gray-100">
          <Icon name="trash" className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}

function TaskChecklist({ wo, task, canEdit, onChange, onComplete }) {
  if (!task.checklist_version) {
    return <p className="text-gray-500 text-sm text-center py-6">Esta tarea no tiene checklist asociado.</p>
  }
  const responseId = task.checklist?.response_id ?? task.checklist_response_id
  if (!responseId) {
    return <NoResponseView task={task} assigned={!!wo.assigned_to} canStart={canEdit} onStart={onChange} />
  }
  return (
    <ChecklistResponseView
      responseId={responseId}
      workOrderId={wo.id}
      canEdit={canEdit}
      onChange={onChange}
      onComplete={onComplete}
    />
  )
}

/**
 * Solo para OTs anteriores a la fase 3: las nuevas traen el checklist creado
 * desde que la tarea entra en la OT.
 */
function NoResponseView({ task, assigned, canStart, onStart }) {
  const createMut = useCreateChecklistResponse()
  const [startError, setStartError] = useState('')

  async function handleStart() {
    setStartError('')
    try {
      await createMut.mutateAsync({ task: task.id, version: task.checklist_version.id })
      onStart()
    } catch (err) {
      const data = err?.response?.data
      const first = data && typeof data === 'object' ? Object.values(data).flat()[0] : data
      setStartError(String(first ?? 'No se pudo iniciar el checklist.'))
    }
  }

  return (
    <div className="text-center py-8 space-y-4">
      <Icon name="checklist" className="w-10 h-10 mx-auto text-gray-400" />
      <div>
        <p className="font-medium text-gray-700">{task.checklist_version.template_name}</p>
        <p className="text-sm text-gray-500">Versión v{task.checklist_version.version_number}</p>
      </div>
      {canStart ? (
        <button onClick={handleStart} disabled={createMut.isPending}
          className="px-5 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60 transition-colors">
          {createMut.isPending ? 'Iniciando...' : 'Iniciar checklist'}
        </button>
      ) : (
        <p className="text-xs text-gray-500">
          {assigned
            ? 'Solo el técnico asignado puede iniciar el checklist.'
            : 'Asigna un técnico a esta OT para iniciar el checklist.'}
        </p>
      )}
      {startError && <p className="text-sm text-red-600">{startError}</p>}
    </div>
  )
}

function ChecklistResponseView({ responseId, workOrderId, canEdit, onChange, onComplete }) {
  const { data: response, isLoading, isError, error, refetch } = useChecklistResponse(responseId)

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner small />
      </div>
    )
  }
  if (isError) return <p className="text-sm text-amber-700 text-center py-6">{error?.message}</p>
  if (!response) return null

  if (response.completed_at) {
    return <CompletedChecklistView response={response} />
  }

  return (
    <ActiveChecklistForm
      key={response.id}
      response={response}
      workOrderId={workOrderId}
      canEdit={canEdit}
      onFieldSaved={() => {
        refetch()
        onChange?.()
      }}
      onComplete={() => {
        refetch()
        onComplete?.()
      }}
    />
  )
}

// ── Agregar y quitar tareas (antes de empezar) ───────────────────────────────

function AddTasksModal({ wo, onClose, onDone }) {
  const { data: pendientes = [], isLoading } = useTasks({ status: 'PENDING', hospital_id: wo.hospital?.id })
  const addMut = useAddWorkOrderTasks(wo.id)
  const [marcadas, setMarcadas] = useState(() => new Set())
  const [avisos, setAvisos] = useState(null)

  function toggle(id) {
    setMarcadas((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleAdd() {
    try {
      const res = await addMut.mutateAsync([...marcadas])
      onDone()
      if (res.warnings?.length) setAvisos(res.warnings)
      else onClose()
    } catch {
      // el error se muestra abajo
    }
  }

  return (
    <Modal title="Agregar tareas a la OT" subtitle={`Pendientes de ${wo.hospital?.name}`} onClose={onClose} width="max-w-2xl">
      <div className="space-y-4">
        {avisos ? (
          <>
            {avisos.map((a) => (
              <p key={a} className="text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2">{a}</p>
            ))}
            <div className="flex justify-end">
              <button onClick={onClose} className="px-4 py-2 bg-brand text-white text-sm rounded-lg">Cerrar</button>
            </div>
          </>
        ) : (
          <>
            <div className="border border-gray-100 rounded-lg max-h-80 overflow-y-auto divide-y divide-gray-50">
              {isLoading ? (
                <div className="flex justify-center py-8"><Spinner small /></div>
              ) : pendientes.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-8">No hay tareas pendientes en este hospital.</p>
              ) : pendientes.map((t) => (
                <label key={t.id} className="flex items-start gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer">
                  <input type="checkbox" checked={marcadas.has(t.id)} onChange={() => toggle(t.id)} className="mt-1" />
                  <span className="min-w-0 text-sm">
                    <span className="font-mono text-xs text-gray-500">{t.asset.code}</span>{' '}
                    <span className="text-gray-800">{t.asset.name}</span>
                    <span className="block text-xs text-gray-500">
                      {t.title} · {formatDate(t.scheduled_date)}{t.asset.node_path && ` · ${t.asset.node_path}`}
                    </span>
                  </span>
                </label>
              ))}
            </div>
            {addMut.isError && (
              <p className="text-sm text-red-600">
                {addMut.error?.response?.data?.detail ?? 'No se pudieron agregar las tareas.'}
              </p>
            )}
            <div className="flex justify-end gap-3">
              <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancelar</button>
              <button onClick={handleAdd} disabled={marcadas.size === 0 || addMut.isPending}
                className="px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60">
                {addMut.isPending ? 'Agregando...' : `Agregar ${marcadas.size || ''}`.trim()}
              </button>
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}

function RemoveTaskModal({ wo, task, onClose, onDone }) {
  const removeMut = useRemoveWorkOrderTask(wo.id)

  async function handleRemove() {
    try {
      await removeMut.mutateAsync(task.id)
      onDone()
      onClose()
    } catch {
      // el error se muestra abajo
    }
  }

  return (
    <Modal title={`Quitar ${task.asset.code} de la OT`} onClose={onClose} width="max-w-md">
      <div className="space-y-4 text-sm text-gray-600">
        <p>{task.asset.name} vuelve a tareas pendientes con su fecha, lista para otra OT.</p>
        {removeMut.isError && (
          <p className="text-red-600">{removeMut.error?.response?.data?.detail ?? 'No se pudo quitar la tarea.'}</p>
        )}
        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-gray-600 hover:text-gray-800">Cancelar</button>
          <button onClick={handleRemove} disabled={removeMut.isPending}
            className="px-4 py-2 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 disabled:opacity-60">
            {removeMut.isPending ? 'Quitando...' : 'Quitar'}
          </button>
        </div>
      </div>
    </Modal>
  )
}

function groupFields(fields) {
  const groups = []
  const map = {}
  for (const f of fields) {
    const key = f.group || ''
    if (!map[key]) {
      map[key] = { name: key, fields: [] }
      groups.push(map[key])
    }
    map[key].fields.push(f)
  }
  return groups.length ? groups : [{ name: '', fields }]
}

function ActiveChecklistForm({ response, workOrderId, canEdit, onFieldSaved, onComplete }) {
  const allFields = response.version_fields ?? []
  const fieldResponses = response.field_responses ?? []

  // Clave de cada respuesta: campo y toma. En un bloque repetible el mismo
  // campo se responde una vez por toma.
  const answeredMap = Object.fromEntries(
    fieldResponses.map((fr) => [slotKey(fr.field, fr.repetition), fr])
  )

  const groups = groupFields(allFields)
  const [groupIdx, setGroupIdx] = useState(0)
  const currentGroup = groups[groupIdx] ?? { name: '', fields: [] }
  const grupoRepetible = isRepeatable(response, currentGroup.name)

  const [localValues, setLocalValues] = useState(() => {
    const init = {}
    fieldResponses.forEach((fr) => { init[slotKey(fr.field, fr.repetition)] = fr.value })
    return init
  })

  const submitFieldMut = useSubmitField(response.id)
  const completeMut = useCompleteChecklist(response.id)
  const blockCountMut = useSetBlockCount(response.id)
  // Rechazos permanentes (4xx) por campo, para poder avisar al tecnico en vez
  // de tragarlos como si fueran falta de red.
  const [fieldErrors, setFieldErrors] = useState({})

  const isOnline = useNetworkStore((s) => s.isOnline)
  const refreshPendingCount = useNetworkStore((s) => s.refreshPendingCount)

  // Cachear el checklist en SQLite: sin esta fila el tecnico no puede abrirlo
  // sin red, y el indicador de pendientes no sabria a que OT pertenece.
  useEffect(() => {
    // Lo leido de SQLite ya esta ahi, con las respuestas locales encima: no
    // se vuelve a guardar como si viniera del servidor.
    if (response._fromOffline) return
    saveChecklistResponse({ ...response, work_order: workOrderId }).catch((error) =>
      console.warn('[Checklist] no se pudo cachear la respuesta:', error?.message ?? error)
    )
  }, [response, workOrderId])

  const esperadas = slots(response)
  const respondida = (x) => !!answeredMap[slotKey(x.field.id, x.repetition)]
  const answeredCount = esperadas.filter(respondida).length
  const totalCount = esperadas.length
  const requiredUnanswered = esperadas.filter((x) => x.field.is_required && !respondida(x))
  const canComplete = requiredUnanswered.length === 0
  const isLastGroup = groupIdx === groups.length - 1

  /** Respuestas escritas que aun no llegaron al servidor (nadie disparo el blur). */
  function pendingKeys() {
    return Object.keys(localValues).filter(
      (k) => (localValues[k] ?? '') !== (answeredMap[k]?.value ?? '')
    )
  }

  /**
   * Guarda la respuesta de un campo en una toma (0 si el campo no se repite).
   *
   * `valorExplicito` existe para los campos que se contestan de un toque
   * (si/no, seleccion, foto). Antes hacian `onChange(v); setTimeout(onBlur, 0)`
   * y el onBlur programado era el cierre de la renderizacion anterior, asi que
   * leia de `localValues` el valor VIEJO. Con el guard de mas abajo eso salia
   * sin enviar nada: el toque se perdia, la interfaz ya mostraba la respuesta
   * nueva y al recargar reaparecia la vieja. En un checklist de cumplimiento
   * eso es un acta que afirma lo contrario de lo que verifico el tecnico.
   */
  async function handleBlur(fieldId, repetition, valorExplicito) {
    if (!canEdit) return
    const key = slotKey(fieldId, repetition)
    const value = valorExplicito !== undefined
      ? valorExplicito
      : (localValues[key] ?? '')
    if (answeredMap[key]?.value === value) return

    // Siempre a SQLite primero: es la unica escritura que no puede fallar.
    await saveFieldResponse({
      id: newId(),
      response_id: response.id,
      field_id: fieldId,
      repetition,
      value,
      notes: '',
      answered_at: new Date().toISOString(),
      synced: 0,
    })

    if (!isOnline) {
      await refreshPendingCount()
      // Relee el checklist y la OT desde SQLite para que el avance se mueva.
      onFieldSaved()
      return
    }

    try {
      await submitFieldMut.mutateAsync({ field: fieldId, repetition, value, notes: '' })
      await markFieldResponseSynced(response.id, fieldId, repetition)
      setFieldErrors((prev) => {
        if (!prev[key]) return prev
        const { [key]: _, ...resto } = prev
        return resto
      })
      onFieldSaved()
    } catch (err) {
      const status = err?.response?.status
      // Un 4xx es permanente: el valor no vale y reintentarlo nunca va a
      // funcionar. Antes se encolaba igual que un corte de red y el tecnico no
      // veia nada, asi que la respuesta se perdia en silencio.
      if (status >= 400 && status < 500) {
        const data = err.response?.data
        const detalle = data?.value ?? data?.repetition ?? data?.detail
        setFieldErrors((prev) => ({
          ...prev,
          [key]: Array.isArray(detalle)
            ? String(detalle[0])
            : typeof detalle === 'string'
              ? detalle
              : 'No se pudo guardar esta respuesta. Revisa el valor.',
        }))
        console.warn('[Checklist] submit-field rechazado:', data)
      } else {
        // Sin respuesta o 5xx: transitorio. Queda en cola y se reintenta.
        console.warn(
          '[Checklist] submit-field fallo, guardado offline:',
          err?.response?.data ?? err?.message
        )
      }
    }
    await refreshPendingCount()
  }

  // ── Cantidad de tomas ──────────────────────────────────────────────────────

  const [countError, setCountError] = useState('')

  /**
   * El tecnico encontro otra cantidad que la del plan. Con red va al servidor;
   * sin red queda en el telefono y en cola, antes que las respuestas.
   */
  async function cambiarCantidad(grupo, nueva) {
    setCountError('')
    if (isOnline) {
      try {
        await blockCountMut.mutateAsync({ group: grupo, count: nueva })
        onFieldSaved()
        return
      } catch (err) {
        if (err?.response) {
          const data = err.response.data
          const detalle = data?.count ?? data?.group ?? data?.detail
          setCountError(Array.isArray(detalle) ? String(detalle[0]) : String(detalle ?? 'No se pudo cambiar la cantidad.'))
          return
        }
        // Sin respuesta del servidor: se guarda en el telefono como sin red.
      }
    }
    await setBlockCountOffline(response.id, { ...(response.block_counts ?? {}), [grupo]: nueva })
    await refreshPendingCount()
    onFieldSaved()
  }

  const [completeError, setCompleteError] = useState('')

  /** Sin red el cierre queda en cola; el motor lo sube despues de las respuestas. */
  async function completarSinRed() {
    await markChecklistCompletedOffline(response.id)
    await refreshPendingCount()
    onComplete()
  }

  async function handleComplete() {
    if (!canComplete) return
    setCompleteError('')
    try {
      // Volcar primero lo que sigue solo en el formulario.
      for (const key of pendingKeys()) {
        const corte = key.lastIndexOf(':')
        await handleBlur(key.slice(0, corte), Number(key.slice(corte + 1)))
      }
      if (!isOnline) {
        await completarSinRed()
        return
      }
      await completeMut.mutateAsync()
      onComplete()
    } catch (err) {
      // Sin respuesta del servidor es la red: se cierra en el telefono.
      if (!err?.response) {
        await completarSinRed()
        return
      }
      const data = err.response.data
      setCompleteError(
        data?.detail ?? 'No se pudo finalizar el checklist. Revisa los campos e intenta de nuevo.'
      )
    }
  }

  function renderField(field, repetition) {
    const key = slotKey(field.id, repetition)
    return (
      <div key={key}>
        <ChecklistFieldInput
          field={field}
          workOrderId={workOrderId}
          taskId={response.task}
          value={localValues[key] ?? ''}
          fieldResponse={answeredMap[key]}
          disabled={!canEdit}
          onChange={(val) => setLocalValues((prev) => ({ ...prev, [key]: val }))}
          onBlur={() => handleBlur(field.id, repetition)}
          // Los campos de un solo toque commitean el valor directamente:
          // no pueden depender de leerlo del estado en el mismo ciclo.
          onCommit={(val) => {
            setLocalValues((prev) => ({ ...prev, [key]: val }))
            handleBlur(field.id, repetition, val)
          }}
        />
        {fieldErrors[key] && (
          <p className="mt-1 text-xs text-red-600">{fieldErrors[key]}</p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Progress */}
      <div>
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>{answeredCount} de {totalCount} campos completados</span>
          <span>{totalCount ? Math.round((answeredCount / totalCount) * 100) : 0}%</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-1.5">
          <div
            className="bg-brand rounded-full h-1.5 transition-all"
            style={{ width: `${totalCount ? (answeredCount / totalCount) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* Group tabs */}
      {groups.length > 1 && (
        <div className="flex gap-1.5 overflow-x-auto pb-1">
          {groups.map((g, i) => (
            <button
              key={i}
              onClick={() => setGroupIdx(i)}
              className={`px-3 py-1.5 text-xs rounded-lg whitespace-nowrap transition-colors ${
                groupIdx === i
                  ? 'bg-brand text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {g.name || 'General'}
              {isRepeatable(response, g.name) && ` × ${countFor(response, g.name)}`}
            </button>
          ))}
        </div>
      )}

      {/* Fields */}
      {grupoRepetible ? (
        <RepeatedGroup
          key={currentGroup.name}
          response={response}
          group={currentGroup}
          answeredMap={answeredMap}
          canEdit={canEdit}
          renderField={renderField}
          onChangeCount={cambiarCantidad}
          busy={blockCountMut.isPending}
          error={countError}
        />
      ) : (
        <div className="space-y-5">
          {currentGroup.fields.map((field) => renderField(field, 0))}
        </div>
      )}

      {/* Navigation / Complete */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        <div className="flex gap-2">
          {groupIdx > 0 && (
            <button
              onClick={() => setGroupIdx((i) => i - 1)}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50"
            >
              <Icon name="chevronLeft" className="w-4 h-4" />
              Anterior
            </button>
          )}
          {!isLastGroup && (
            <button
              onClick={() => setGroupIdx((i) => i + 1)}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50"
            >
              Siguiente
              <Icon name="chevronRight" className="w-4 h-4" />
            </button>
          )}
        </div>

        {isLastGroup && canEdit && (
          <div className="flex items-center gap-2">
            {!canComplete && (
              <span className="text-xs text-orange-500">
                {requiredUnanswered.length} campo(s) obligatorio(s) pendiente(s)
              </span>
            )}
            <button
              onClick={handleComplete}
              disabled={!canComplete || completeMut.isPending}
              className="inline-flex items-center gap-1.5 px-5 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {!completeMut.isPending && <Icon name="check" className="w-4 h-4" />}
              {completeMut.isPending ? 'Finalizando...' : 'Finalizar checklist'}
            </button>
          </div>
        )}
      </div>

      {completeError && (
        <p className="text-sm text-red-600 text-right">{completeError}</p>
      )}
    </div>
  )
}

/**
 * Un bloque repetible: una tarjeta por toma, abierta de a una para que 30
 * tomas no sean 270 campos en pantalla. Abajo, agregar o quitar tomas si en
 * campo hay otra cantidad que la del plan.
 */
function RepeatedGroup({ response, group, answeredMap, canEdit, renderField, onChangeCount, busy, error }) {
  const cuantas = countFor(response, group.name)
  const planeadas = response.planned_block_counts?.[group.name]
  const respondidasDe = (n) => group.fields.filter((f) => answeredMap[slotKey(f.id, n)]).length
  const faltanDe = (n) =>
    group.fields.filter((f) => f.is_required && !answeredMap[slotKey(f.id, n)]).length
  const numeros = Array.from({ length: cuantas }, (_, i) => i + 1)
  const [abierta, setAbierta] = useState(
    () => numeros.find((n) => respondidasDe(n) < group.fields.length) ?? 1
  )
  const ultimaVacia = cuantas > 1 && respondidasDe(cuantas) === 0
  const nombre = group.name.toLowerCase()

  return (
    <div className="space-y-2">
      {planeadas && planeadas !== cuantas && (
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          El plan dice {planeadas} y aquí hay {cuantas}. Se le avisará al administrador.
        </p>
      )}
      {numeros.map((n) => {
        const respondidas = respondidasDe(n)
        const completa = respondidas === group.fields.length
        return (
          <div key={n} className="border border-gray-200 rounded-xl overflow-hidden">
            <button
              type="button"
              onClick={() => setAbierta(abierta === n ? null : n)}
              aria-expanded={abierta === n}
              className="w-full flex items-center justify-between gap-3 px-4 py-2.5 text-left hover:bg-gray-50"
            >
              <span className="text-sm font-medium text-gray-800">{group.name} {n}</span>
              <span className={`text-xs ${completa ? 'text-green-600' : faltanDe(n) ? 'text-orange-500' : 'text-gray-500'}`}>
                {completa ? 'Completa' : `${respondidas} de ${group.fields.length}`}
              </span>
            </button>
            {abierta === n && (
              <div className="border-t border-gray-100 p-4 space-y-5 bg-gray-50/40">
                {group.fields.map((field) => renderField(field, n))}
                {n < cuantas && (
                  <button type="button" onClick={() => setAbierta(n + 1)}
                    className="text-sm text-brand hover:underline">
                    Siguiente: {group.name} {n + 1}
                  </button>
                )}
              </div>
            )}
          </div>
        )
      })}

      {canEdit && (
        <div className="flex items-center gap-3 flex-wrap pt-1">
          <button type="button" disabled={busy}
            onClick={() => { onChangeCount(group.name, cuantas + 1); setAbierta(cuantas + 1) }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-50">
            <Icon name="plus" className="w-4 h-4" /> Agregar {nombre}
          </button>
          {ultimaVacia && (
            <button type="button" disabled={busy}
              onClick={() => onChangeCount(group.name, cuantas - 1)}
              className="text-sm text-gray-500 hover:text-red-600 disabled:opacity-50">
              Quitar {nombre} {cuantas} (vacía)
            </button>
          )}
        </div>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}

function ChecklistFieldInput({ field, workOrderId, taskId, value, fieldResponse, disabled, onChange, onBlur, onCommit }) {
  const ft = getFieldType(field.field_type)
  const isAnswered = !!fieldResponse
  const isOutOfRange = fieldResponse?.out_of_range
  const opts = Array.isArray(field.options_json) ? field.options_json : []
  const minMax =
    typeof field.options_json === 'object' &&
    !Array.isArray(field.options_json) &&
    field.options_json !== null
      ? field.options_json
      : {}

  function getMultiValues() {
    try { return JSON.parse(value || '[]') } catch { return [] }
  }

  const inputCls =
    'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 disabled:bg-gray-50 disabled:text-gray-500'

  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-gray-700">
        {field.label}
        {field.is_required && <span className="text-red-500 ml-0.5">*</span>}
        {isAnswered && !isOutOfRange && <span className="ml-2 inline-flex items-center gap-1 text-xs text-green-600 font-normal"><Icon name="check" className="w-3.5 h-3.5" />guardado</span>}
        {isOutOfRange && (
          <span className="ml-2 inline-flex items-center gap-1 text-xs text-red-600 font-normal">
            <Icon name="warning" className="w-3.5 h-3.5" />fuera de rango
          </span>
        )}
      </label>
      {field.help_text && <p className="text-xs text-gray-500">{field.help_text}</p>}

      {/* TEXT */}
      {field.field_type === 'TEXT' && (
        <input
          type="text"
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          className={inputCls}
          placeholder="Respuesta..."
        />
      )}

      {/* TEXTAREA */}
      {field.field_type === 'TEXTAREA' && (
        <textarea
          rows={3}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          className={`${inputCls} resize-none`}
          placeholder="Respuesta..."
        />
      )}

      {/* NUMBER / METER */}
      {(field.field_type === 'NUMBER' || field.field_type === 'METER') && (
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={value}
            disabled={disabled}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            className={`${inputCls} w-36 ${isOutOfRange ? 'border-red-400 focus:ring-red-300' : ''}`}
            placeholder="0"
          />
          {minMax.unit && <span className="text-sm text-gray-500">{minMax.unit}</span>}
          {(minMax.min !== undefined || minMax.max !== undefined) && (
            <span className="text-xs text-gray-500">
              [{minMax.min ?? '—'} — {minMax.max ?? '—'}]
            </span>
          )}
        </div>
      )}

      {/* BOOLEAN */}
      {field.field_type === 'BOOLEAN' && (
        <div className="flex gap-2">
          {['true', 'false'].map((v) => (
            <button
              key={v}
              type="button"
              disabled={disabled}
              onClick={() => onCommit(v)}
              className={`px-5 py-2 rounded-lg border text-sm font-medium transition-colors disabled:cursor-default ${
                value === v
                  ? v === 'true'
                    ? 'bg-green-600 text-white border-green-600'
                    : 'bg-red-500 text-white border-red-500'
                  : 'border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {v === 'true' ? 'Sí' : 'No'}
            </button>
          ))}
        </div>
      )}

      {/* SELECT */}
      {field.field_type === 'SELECT' && (
        <select
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          className={inputCls}
        >
          <option value="">Seleccionar...</option>
          {opts.filter(Boolean).map((o, i) => (
            <option key={i} value={o}>{o}</option>
          ))}
        </select>
      )}

      {/* MULTI_SELECT */}
      {field.field_type === 'MULTI_SELECT' && (
        <div className="space-y-1.5">
          {opts.filter(Boolean).map((o, i) => {
            const selected = getMultiValues()
            const checked = selected.includes(o)
            return (
              <label key={i} className={`flex items-center gap-2 text-sm ${disabled ? 'cursor-default text-gray-500' : 'cursor-pointer text-gray-700'}`}>
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={disabled}
                  onChange={() => {
                    const next = checked ? selected.filter((v) => v !== o) : [...selected, o]
                    onCommit(JSON.stringify(next))
                  }}
                  className="rounded border-gray-300 text-brand focus:ring-brand"
                />
                {o}
              </label>
            )
          })}
        </div>
      )}

      {/* DATE */}
      {field.field_type === 'DATE' && (
        <input
          type="date"
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          className={inputCls}
        />
      )}

      {/* DATETIME */}
      {field.field_type === 'DATETIME' && (
        <input
          type="datetime-local"
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          className={inputCls}
        />
      )}

      {/* GPS */}
      {field.field_type === 'GPS' && (
        <div className="flex items-center gap-2">
          <div className={`flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm ${value ? 'text-gray-700' : 'text-gray-500'}`}>
            {value || 'Sin ubicación capturada'}
          </div>
          {!disabled && (
            <button
              type="button"
              onClick={() => {
                if (!navigator.geolocation) return
                navigator.geolocation.getCurrentPosition(
                  (pos) => {
                    const v = `${pos.coords.latitude.toFixed(6)},${pos.coords.longitude.toFixed(6)}`
                    onCommit(v)
                  },
                  (err) => console.error('GPS error', err)
                )
              }}
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-brand/10 text-brand text-sm rounded-lg hover:bg-brand/20 transition-colors whitespace-nowrap"
            >
              <Icon name="area" className="w-4 h-4" />
              Capturar
            </button>
          )}
        </div>
      )}

      {/* PHOTO */}
      {field.field_type === 'PHOTO' && (
        <ChecklistPhotoField
          workOrderId={workOrderId}
          taskId={taskId}
          value={value}
          disabled={disabled}
          onCommit={onCommit}
        />
      )}

      {/* SIGNATURE */}
      {field.field_type === 'SIGNATURE' && (
        <div className="flex items-center gap-2 px-3 py-2.5 border border-gray-200 rounded-lg bg-gray-50">
          <Icon name="signature" className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-500">
            La firma se registra en la pestaña Evidencia.
          </span>
        </div>
      )}
    </div>
  )
}

/**
 * Campo PHOTO del checklist.
 *
 * Sube la imagen a la evidencia de la OT, ligada a la tarea para que en el
 * acta salga en el bloque de su activo, y guarda `foto:<id>` como valor del
 * campo. No guarda la URL: en S3 va firmada y caduca a las 24 horas, y el
 * enlace "ver" dejaba de abrir al dia siguiente.
 *
 * En el telefono abre la camara, como la pestaña Evidencia: el selector de
 * archivos de Android abre la galeria, y en campo la foto se toma ahi mismo.
 * Sin red la foto queda en la cola de SQLite y el campo guarda
 * `sin-conexion:<uuid>`; la foto se sube con el resto al reconectar.
 */
const FOTO = 'foto:'
const SIN_CONEXION = 'sin-conexion:'

/**
 * Enlace a la foto de un campo del checklist, con su URL recien firmada.
 *
 * La busca en la evidencia de la OT: por id (`foto:<id>`) o, si se tomo sin
 * red, por el offline_uuid con que se sincronizo. Los valores de antes de este
 * cambio son la URL misma.
 */
function FotoDelChecklist({ workOrderId, value }) {
  const isOnline = useNetworkStore((s) => s.isOnline)
  const guardaReferencia = value.startsWith(FOTO) || value.startsWith(SIN_CONEXION)
  const { data: fotos = [], isLoading } = useWorkOrderPhotos(
    isOnline && guardaReferencia ? workOrderId : null
  )

  let url = guardaReferencia ? null : value
  if (value.startsWith(FOTO)) {
    url = fotos.find((f) => f.id === value.slice(FOTO.length))?.file_url
  } else if (value.startsWith(SIN_CONEXION)) {
    url = fotos.find((f) => f.offline_uuid === value.slice(SIN_CONEXION.length))?.file_url
  }

  let nota = null
  if (!url && value.startsWith(SIN_CONEXION)) nota = 'tomada sin conexión, se sube con la evidencia'
  else if (!url && !isOnline) nota = 'se puede ver con conexión'
  else if (!url && !isLoading) nota = 'no se encontró en la evidencia de la OT'

  return (
    <span className="inline-flex items-center gap-1 text-green-600">
      <Icon name="camera" className="w-3.5 h-3.5 flex-shrink-0" />
      Foto adjunta
      {url ? (
        <a href={mediaUrl(url)} target="_blank" rel="noopener noreferrer" className="text-brand hover:underline">
          ver
        </a>
      ) : nota && (
        <span className="text-gray-500">· {nota}</span>
      )}
    </span>
  )
}

function ChecklistPhotoField({ workOrderId, taskId, value, disabled, onCommit }) {
  const uploadPhoto = useUploadPhoto()
  const isOnline = useNetworkStore((s) => s.isOnline)
  const refreshPendingCount = useNetworkStore((s) => s.refreshPendingCount)
  const [error, setError] = useState('')
  const [capturando, setCapturando] = useState(false)
  const nativo = Capacitor.isNativePlatform()
  const ocupado = uploadPhoto.isPending || capturando

  async function guardarSinRed(dataUrl, takenAt) {
    const offlineUuid = await savePhotoOffline({
      work_order_id: workOrderId,
      file_path: dataUrl,
      latitude: null,
      longitude: null,
      taken_at: takenAt,
      caption: 'Checklist',
      task_id: taskId || null,
    })
    if (!offlineUuid) {
      setError('No hay base de datos local disponible para guardar la foto.')
      return
    }
    await refreshPendingCount()
    onCommit(`${SIN_CONEXION}${offlineUuid}`)
  }

  async function subir(file, dataUrl = null) {
    setError('')
    const takenAt = new Date().toISOString()
    if (dataUrl && !isOnline) return guardarSinRed(dataUrl, takenAt)
    try {
      const photo = await uploadPhoto.mutateAsync({
        work_order: workOrderId,
        task: taskId || null,
        file,
        taken_at: takenAt,
        caption: 'Checklist',
      })
      onCommit(`${FOTO}${photo.id}`)
    } catch (err) {
      // No llego al servidor: en el telefono se guarda para subirla despues.
      if (!err?.response && dataUrl) return guardarSinRed(dataUrl, takenAt)
      if (!err?.response) {
        setError('No se pudo conectar con el servidor. Revisa la conexión e intenta de nuevo.')
        return
      }
      const detail = err.response.data
      const first = detail && typeof detail === 'object' ? Object.values(detail).flat()[0] : detail
      setError(String(first ?? 'No se pudo subir la foto.'))
    }
  }

  async function handleFile(event) {
    const file = event.target.files?.[0]
    // Permite volver a elegir el mismo archivo despues de un fallo.
    event.target.value = ''
    if (file) await subir(file)
  }

  async function tomarFoto() {
    setError('')
    setCapturando(true)
    try {
      const photo = await Camera.getPhoto({
        quality: 80,
        allowEditing: false,
        resultType: CameraResultType.Base64,
        source: CameraSource.Camera,
        saveToGallery: false,
        correctOrientation: true,
        width: 1920,
      })
      const mime = photo.format === 'png' ? 'image/png' : 'image/jpeg'
      const dataUrl = `data:${mime};base64,${photo.base64String}`
      await subir(await dataUrlToFile(dataUrl, `checklist-${Date.now()}`), dataUrl)
    } catch (err) {
      // Cancelar la camara tambien llega aqui; no es un error.
      const message = err?.message ?? ''
      if (!/cancel/i.test(message)) setError(message || 'No se pudo abrir la cámara.')
    } finally {
      setCapturando(false)
    }
  }

  const botonCls = `inline-flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg text-sm transition-colors ${
    ocupado ? 'text-gray-400 cursor-wait' : 'text-gray-600 hover:bg-gray-50 cursor-pointer'
  }`
  const botonTexto = (
    <>
      {ocupado ? <Spinner small /> : <Icon name="camera" className="w-4 h-4" />}
      {capturando ? 'Abriendo cámara...' : uploadPhoto.isPending ? 'Subiendo...' : nativo ? 'Tomar foto' : 'Seleccionar foto'}
    </>
  )

  return (
    <div>
      {value && !ocupado && (
        <p className="text-xs mb-1">
          <FotoDelChecklist workOrderId={workOrderId} value={value} />
        </p>
      )}
      {!disabled && (nativo ? (
        <button type="button" onClick={tomarFoto} disabled={ocupado} className={botonCls}>
          {botonTexto}
        </button>
      ) : (
        // relative: el input sr-only es absoluto; sin esto se posiciona respecto
        // al marco de la app y al enfocarlo el navegador desplaza el marco.
        <label className={`relative ${botonCls}`}>
          {botonTexto}
          <input
            type="file"
            accept="image/*"
            className="sr-only"
            disabled={ocupado}
            onChange={handleFile}
          />
        </label>
      ))}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}

// ── Repuestos tab ─────────────────────────────────────────────────────────────

function RepuestosTab({ wo, user }) {
  const role = user?.role
  const canAdd = ['ADMIN', 'TEC'].includes(role) && wo.status === 'IN_PROGRESS'
  const isTec = role === 'TEC'
  const isTecAssigned = isTec && wo.assigned_to?.id === user?.id

  const { data: movements = [], isLoading } = useStockMovements({ work_order_id: wo.id })
  const [showModal, setShowModal] = useState(false)

  const canShowAddButton = canAdd && (role === 'ADMIN' || isTecAssigned)

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          Materiales y repuestos utilizados en esta orden.
        </p>
        {canShowAddButton && (
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light transition-colors"
          >
            Agregar repuesto
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8"><Spinner /></div>
      ) : movements.length === 0 ? (
        <p className="text-center py-8 text-gray-500 text-sm">Sin repuestos registrados.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-100">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr className="text-left text-xs font-medium text-gray-500">
                <th className="px-4 py-3">Item</th>
                <th className="px-4 py-3">Codigo</th>
                <th className="px-4 py-3">Cantidad</th>
                <th className="px-4 py-3">Unidad</th>
                <th className="px-4 py-3">Costo unit.</th>
                <th className="px-4 py-3">Fecha</th>
                <th className="px-4 py-3">Registrado por</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {movements.map((mov) => (
                <tr key={mov.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{mov.item?.name ?? '—'}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{mov.item?.code ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{parseFloat(mov.quantity).toLocaleString('es-CO')}</td>
                  <td className="px-4 py-3 text-gray-500">{mov.item?.unit_of_measure ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {mov.item?.unit_cost ? `$${parseFloat(mov.item.unit_cost).toLocaleString('es-CO')}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                    {new Date(mov.performed_at).toLocaleDateString('es-CO')}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {mov.performed_by?.full_name ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <RepuestoModal wo={wo} onClose={() => setShowModal(false)} />
      )}
    </div>
  )
}

function RepuestoModal({ wo, onClose }) {
  useModalDismiss(onClose)
  const createMut = useCreateStockMovement()
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [selectedItem, setSelectedItem] = useState(null)
  const [quantity, setQuantity] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [errorTimer, setErrorTimer] = useState(null)

  const { data: items = [] } = useInventoryItems(debouncedSearch ? { search: debouncedSearch } : {})
  const activeItems = items.filter((i) => i.is_active)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 400)
    return () => clearTimeout(t)
  }, [search])

  function showError(msg) {
    if (errorTimer) clearTimeout(errorTimer)
    setError(msg)
    const t = setTimeout(() => setError(''), 4000)
    setErrorTimer(t)
  }

  async function handleSave() {
    if (!selectedItem) { showError('Selecciona un item.'); return }
    const qty = parseFloat(quantity)
    if (!quantity || isNaN(qty) || qty <= 0) { showError('Ingresa una cantidad valida.'); return }
    try {
      await createMut.mutateAsync({
        item: selectedItem.id,
        movement_type: 'OUT',
        quantity,
        work_order: wo.id,
        notes,
      })
      onClose()
    } catch (err) {
      const detail = err?.response?.data
      if (typeof detail === 'string') showError(detail)
      else if (typeof detail === 'object') showError(Object.values(detail).flat().join(' '))
      else showError('Error al registrar el repuesto.')
    }
  }

  const inp = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-[2px]">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
        <div className="flex items-start justify-between gap-4 mb-4">
          <h3 className="text-lg font-semibold text-gray-800">Registrar repuesto usado</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="p-1 -mr-1 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <Icon name="close" className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Buscar item *</label>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className={inp}
              placeholder="Nombre o codigo..."
            />
            {activeItems.length > 0 && !selectedItem && (
              <ul className="mt-1 border border-gray-200 rounded-lg max-h-36 overflow-y-auto divide-y divide-gray-50">
                {activeItems.slice(0, 8).map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                      onClick={() => { setSelectedItem(item); setSearch(item.name) }}
                    >
                      <span className="font-medium text-gray-800">{item.name}</span>
                      <span className="ml-2 font-mono text-xs text-gray-500">{item.code}</span>
                      <span className="ml-2 text-xs text-gray-500">
                        Stock: {parseFloat(item.current_stock).toLocaleString('es-CO')} {item.unit_of_measure}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {selectedItem && (
              <div className="mt-1 flex items-center gap-2 px-3 py-2 bg-brand/10 rounded-lg text-sm">
                <span className="text-brand font-medium">{selectedItem.name}</span>
                <span className="text-xs text-gray-500">{selectedItem.code}</span>
                <button type="button" onClick={() => { setSelectedItem(null); setSearch('') }}
                  className="ml-auto text-xs text-gray-500 hover:text-gray-600">
                  Cambiar
                </button>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Cantidad *</label>
            <input type="number" min="0" step="0.01" value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className={inp} placeholder="0" />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notas</label>
            <textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)}
              className={`${inp} resize-none`} />
          </div>

          {error && <p className="text-xs text-red-500 bg-red-50 rounded px-2 py-1">{error}</p>}
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={createMut.isPending}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60"
          >
            {createMut.isPending && (
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            )}
            Registrar
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Reports tab ───────────────────────────────────────────────────────────────

function ReportsTab({ workOrderId, woStatus, reportStatus, role }) {
  const { data: reports = [], isLoading, isError, refetch } = useWorkOrderReports(workOrderId)
  const downloadMut = useReportDownload()
  const resendMut = useResendReportEmail()
  const [confirmResend, setConfirmResend] = useState(null)
  const [gaveUp, setGaveUp] = useState(false)
  const regenerateMut = useRegenerateReport(workOrderId)

  const hasReport = reports.length > 0
  // El backend ya sabe que la generacion fallo (lo registra en auditoria). Sin
  // consultarlo, esta pestaña no distinguia "fallo" de "todavia se genera" y
  // giraba los dos minutos enteros del temporizador antes de rendirse.
  const knownFailure = reportStatus === 'failed'

  // Temporizador explicito. Antes se comparaba contra `dataUpdatedAt`, pero ese
  // valor se refresca en cada sondeo, asi que el umbral no se alcanzaba nunca y
  // la pestaña se quedaba girando para siempre.
  useEffect(() => {
    if (woStatus !== 'COMPLETED' || hasReport) {
      setGaveUp(false)
      return undefined
    }
    if (knownFailure) {
      setGaveUp(true)
      return undefined
    }
    const timer = setTimeout(() => setGaveUp(true), REPORT_POLL_TIMEOUT_MS)
    return () => clearTimeout(timer)
  }, [woStatus, hasReport, knownFailure])

  if (woStatus !== 'COMPLETED') {
    return (
      <p className="text-gray-500 text-sm text-center py-8">
        Los reportes se generan automaticamente al completar la OT.
      </p>
    )
  }

  if (isError) {
    return (
      <div className="py-8 text-center space-y-3">
        <p className="text-sm text-red-600">No se pudo consultar el reporte de esta OT.</p>
        <button onClick={() => refetch()} className="btn-secondary">
          Reintentar
        </button>
      </div>
    )
  }

  if (!hasReport) {
    if (isLoading || !gaveUp) {
      return (
        <div className="flex flex-col items-center gap-3 py-10 text-gray-500">
          <Spinner />
          <p className="text-sm">Generando reporte...</p>
        </div>
      )
    }

    return (
      <div className="py-8 text-center space-y-3">
        <Icon name="warning" className="w-8 h-8 mx-auto text-amber-500" />
        <p className="text-sm text-gray-700">El reporte no se pudo generar.</p>
        <p className="text-xs text-gray-500 max-w-md mx-auto">
          La OT quedo completada correctamente. Revisa la consola del backend:
          si aparece un error de WeasyPrint, faltan las librerias graficas
          (GTK/Pango) que necesita para escribir el PDF.
        </p>
        {role === 'ADMIN' ? (
          <>
            <button
              onClick={async () => {
                setGaveUp(false)
                await regenerateMut.mutateAsync().catch(() => {})
                refetch()
              }}
              disabled={regenerateMut.isPending}
              className="btn-secondary inline-flex items-center gap-2"
            >
              {regenerateMut.isPending && <Spinner small />}
              {regenerateMut.isPending ? 'Generando...' : 'Generar reporte de nuevo'}
            </button>
            {regenerateMut.isError && (
              <p className="text-xs text-red-600">
                {regenerateMut.error?.response?.data?.detail ??
                  'No se pudo relanzar la generacion.'}
              </p>
            )}
          </>
        ) : (
          <p className="text-xs text-gray-500">
            Pide a un administrador que vuelva a generar el reporte.
          </p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {reports.map((report) => (
        <div key={report.id} className="border border-gray-200 rounded-xl p-5 space-y-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="space-y-1 min-w-0">
              <p className="font-medium text-gray-800">{report.title || `Reporte ${formatWoCode(report.work_order)}`}</p>
              <p className="text-xs text-gray-500">
                Generado: {new Date(report.generated_at).toLocaleString('es-CO')}
              </p>
              {report.file_hash && (
                <p className="font-mono text-xs text-gray-500">
                  SHA-256: {report.file_hash.slice(0, 16)}...
                </p>
              )}
            </div>
            <button
              onClick={() => downloadMut.mutate(report.id)}
              disabled={downloadMut.isPending}
              className="flex items-center gap-1.5 px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60 transition-colors whitespace-nowrap"
            >
              {downloadMut.isPending ? <Spinner small /> : null}
              Descargar PDF
            </button>
          </div>

          {/* Send logs */}
          <div>
            <p className="text-xs font-semibold text-gray-500 mb-2">
              Envios por correo
            </p>
            {report.send_logs && report.send_logs.length > 0 ? (
              <ul className="space-y-1">
                {report.send_logs.map((log) => (
                  <li key={log.id} className="flex items-center gap-2 text-xs text-gray-500">
                    <Icon
                      name={log.was_successful ? 'check' : 'close'}
                      className={`w-3.5 h-3.5 flex-shrink-0 ${log.was_successful ? 'text-green-600' : 'text-red-500'}`}
                    />
                    <span>{log.recipient_email}</span>
                    <span className="text-gray-400">·</span>
                    <span>{new Date(log.sent_at).toLocaleString('es-CO')}</span>
                    {!log.was_successful && log.error_message && (
                      <span className="text-red-400">({log.error_message})</span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-gray-500">Sin envios registrados</p>
            )}
          </div>

          {/* Resend — ADMIN only */}
          {role === 'ADMIN' && (
            <div>
              {confirmResend === report.id ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-600">Reenviar email de reporte?</span>
                  <button
                    onClick={() => {
                      resendMut.mutate(report.id)
                      setConfirmResend(null)
                    }}
                    disabled={resendMut.isPending}
                    className="px-3 py-1 text-xs bg-brand text-white rounded-lg hover:bg-brand-light disabled:opacity-60"
                  >
                    Confirmar
                  </button>
                  <button
                    onClick={() => setConfirmResend(null)}
                    className="px-3 py-1 text-xs border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmResend(report.id)}
                  className="text-xs text-brand hover:underline"
                >
                  Reenviar email
                </button>
              )}
            </div>
          )}
        </div>
      ))}

      {role === 'ADMIN' && <IntegritySection workOrderId={workOrderId} />}
    </div>
  )
}

// ── Verificacion de integridad ────────────────────────────────────────────────

function IntegritySection({ workOrderId }) {
  const [checkId, setCheckId] = useState(null)
  const { data, isFetching, error, refetch } = useIntegrityCheck(checkId)

  const detail = error?.response?.data?.detail

  // Volver a pulsar sobre la misma OT no cambia el estado, hay que forzar el refetch.
  function handleCheck() {
    if (checkId) refetch()
    else setCheckId(workOrderId)
  }

  return (
    <div className="border border-gray-200 rounded-xl p-5 space-y-3">
      <p className="text-xs font-semibold text-gray-500">
        Verificacion de integridad
      </p>

      <button
        onClick={handleCheck}
        disabled={isFetching}
        className="btn-secondary inline-flex items-center gap-2"
      >
        {isFetching && <Spinner small />}
        {isFetching ? 'Verificando...' : 'Verificar integridad del documento'}
      </button>

      {!isFetching && error && (
        <div className="px-4 py-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
          {detail || 'No se pudo verificar la integridad del documento.'}
        </div>
      )}

      {!isFetching && data && (
        <div
          className={`px-4 py-3 rounded-lg border text-sm ${
            data.verified
              ? 'bg-green-50 border-green-200 text-green-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}
        >
          <div className="flex items-start gap-2">
            {data.verified ? (
              <svg className="w-5 h-5 flex-shrink-0 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ) : (
              <svg className="w-5 h-5 flex-shrink-0 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              </svg>
            )}
            <p className="font-medium">
              {data.verified
                ? 'Integridad verificada — El documento no ha sido alterado desde su firma'
                : 'ALERTA: Se detectaron modificaciones en el documento despues de su firma'}
            </p>
          </div>
          {data.stored_hash && (
            <p className="font-mono text-xs mt-2 opacity-75 pl-7">
              SHA-256: {data.stored_hash}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function CompletedChecklistView({ response }) {
  const allFields = response.version_fields ?? []
  const fieldResponses = response.field_responses ?? []
  const answeredMap = Object.fromEntries(
    fieldResponses.map((fr) => [slotKey(fr.field, fr.repetition), fr])
  )
  const groups = groupFields(allFields)
  // Un grupo repetible se muestra una vez por toma: [{ titulo, fields, n }].
  const bloques = groups.flatMap((g) =>
    isRepeatable(response, g.name)
      ? Array.from({ length: countFor(response, g.name) }, (_, i) => ({
          titulo: `${g.name} ${i + 1}`, fields: g.fields, n: i + 1,
        }))
      : [{ titulo: g.name, fields: g.fields, n: 0 }]
  )

  return (
    <div className="space-y-6">
      {/* Summary banner */}
      <div className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-xl p-4">
        <Icon name="checkCircle" className="w-7 h-7 flex-shrink-0 text-green-600" />
        <div>
          <p className="text-sm font-semibold text-green-800">Checklist completado</p>
          <p className="text-xs text-green-600">
            {response.started_at && `Inicio: ${new Date(response.started_at).toLocaleString('es-CO')} · `}
            Cierre: {new Date(response.completed_at).toLocaleString('es-CO')}
          </p>
          {response._completionPending && (
            <p className="text-xs text-amber-700 mt-0.5">
              Cerrado en el teléfono. Se enviará al servidor al recuperar la conexión.
            </p>
          )}
        </div>
      </div>

      {/* Read-only answers */}
      {bloques.map((group, gi) => (
        <div key={gi} className="space-y-4">
          {group.titulo && (
            <h3 className="text-xs font-semibold text-gray-500 border-b border-gray-200 pb-2">
              {group.titulo}
            </h3>
          )}
          {group.fields.map((field) => {
            const fr = answeredMap[slotKey(field.id, group.n)]
            return (
              <div key={field.id} className="space-y-1">
                <label className="block text-xs font-medium text-gray-500">
                  {field.label}
                  {fr?.out_of_range && (
                    <span className="ml-2 inline-flex items-center gap-1 text-red-600 normal-case font-normal">
                      <Icon name="warning" className="w-3.5 h-3.5" />fuera de rango
                    </span>
                  )}
                </label>
                <div
                  className={`px-3 py-2 rounded-lg border text-sm ${
                    fr?.out_of_range
                      ? 'bg-red-50 border-red-200 text-red-700'
                      : 'bg-gray-50 border-gray-200 text-gray-700'
                  }`}
                >
                  {!fr?.value ? (
                    <span className="text-gray-500 italic">Sin respuesta</span>
                  ) : field.field_type === 'PHOTO' ? (
                    <FotoDelChecklist workOrderId={response.work_order} value={fr.value} />
                  ) : field.field_type === 'BOOLEAN' ? (
                    ({ true: 'Sí', false: 'No' })[fr.value] ?? fr.value
                  ) : (
                    fr.value
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}
