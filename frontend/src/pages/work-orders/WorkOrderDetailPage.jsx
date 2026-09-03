import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import {
  useWorkOrder,
  useWorkOrderHistory,
  useUpdateWorkOrder,
  useAssignWorkOrder,
} from '../../api/workOrders'
import { useUsers } from '../../api/users'
import { formatWoCode } from '../../utils/workOrder'
import {
  useChecklistResponse,
  useChecklistTemplates,
  useCreateChecklistResponse,
  useSubmitField,
  useCompleteChecklist,
} from '../../api/checklists'
import { getFieldType } from '../../constants/checklistFields'
import StatusBadge from '../../components/workOrders/StatusBadge'
import PriorityBadge from '../../components/workOrders/PriorityBadge'
import TransitionButton from '../../components/workOrders/TransitionButton'
import SignatureList from '../../components/evidence/SignatureList'
import SignaturePad from '../../components/evidence/SignaturePad'
import PhotoGallery from '../../components/evidence/PhotoGallery'
import PhotoCapture from '../../components/evidence/PhotoCapture'
import { useUploadPhoto } from '../../api/evidence'
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
  markFieldResponseSynced,
  newId,
  saveChecklistResponse,
  saveFieldResponse,
} from '../../db/repositories'

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

  const [tab, setTab] = useState(0)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showAssignModal, setShowAssignModal] = useState(false)

  const { data: wo, isLoading, isError, refetch } = useWorkOrder(id)

  // Determine back route by role
  const backPath = role === 'TEC' ? '/mis-ordenes' : '/ordenes'

  if (isLoading) return <div className="flex justify-center py-20"><Spinner /></div>
  if (isError || !wo) {
    return (
      <div className="text-center py-20 text-gray-500">
        <Icon name="warning" className="w-10 h-10 mx-auto mb-3 text-amber-500" />
        <p>No se encontró la OT</p>
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
          <h2 className="font-semibold text-gray-800 text-sm">Activo</h2>
          <dl className="grid grid-cols-2 gap-4">
            <InfoRow label="Código" value={<span className="font-mono">{wo.asset?.code}</span>} />
            <InfoRow label="Nombre" value={wo.asset?.name} />
            <InfoRow label="Hospital" value={wo.hospital?.name} />
          </dl>
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
            {wo.maintenance_plan && <InfoRow label="Plan PM" value={wo.maintenance_plan.name} />}
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
            {['Historial de estados', 'Checklist', 'Evidencia', 'Repuestos', 'Reportes'].map((label, i) => (
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
          {tab === 1 && <ChecklistTab wo={wo} user={user} refetch={refetch} />}
          {tab === 3 && <RepuestosTab wo={wo} user={user} />}
          {tab === 4 && <ReportsTab workOrderId={id} woStatus={wo.status} role={role} />}
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
                  <PhotoCapture workOrderId={id} disabled={wo.status !== 'IN_PROGRESS'} />
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

  // Una vez iniciado el checklist la version queda fija: cambiarla dejaria las
  // respuestas apuntando a campos de otra version.
  const checklistLocked = !!wo.checklist_response_id
  const { data: checklistTemplates = [] } = useChecklistTemplates({ is_active: true })
  const publishedChecklists = checklistTemplates.filter((t) => t.current_version_id)

  const [form, setForm] = useState({
    title: wo.title ?? '',
    description: wo.description ?? '',
    priority: wo.priority ?? 'MEDIUM',
    scheduled_date: wo.scheduled_date ?? '',
    estimated_duration: wo.estimated_duration ? wo.estimated_duration.substring(0, 5) : '',
    assigned_to: wo.assigned_to?.id ?? '',
    checklist_version: wo.checklist_version?.id ?? '',
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
      ...(!checklistLocked && { checklist_version: form.checklist_version || null }),
    }
    await updateMut.mutateAsync(payload)
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
                El checklist ya fue iniciado y no se puede cambiar.
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

function ChecklistTab({ wo, user, refetch }) {
  if (!wo.checklist_version) {
    return (
      <p className="text-gray-500 text-sm text-center py-8">
        Esta OT no tiene checklist asociado.
      </p>
    )
  }

  const isTecAssigned =
    user?.role === 'TEC' && wo.assigned_to?.id === user?.id

  // Misma regla que firmas, fotos y repuestos: solo con la OT en curso.
  const isInProgress = wo.status === 'IN_PROGRESS'
  const canEdit = isTecAssigned && isInProgress

  const notStartedNotice = isTecAssigned && !isInProgress && (
    <div className="mb-4 flex items-start gap-2 px-4 py-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
      <Icon name="warning" className="w-4 h-4 flex-shrink-0 mt-0.5" />
      <span>
        {wo.status === 'PENDING'
          ? 'Inicia la OT para responder el checklist y adjuntar fotos.'
          : 'El checklist solo se puede editar mientras la OT esta en proceso.'}
      </span>
    </div>
  )

  if (!wo.checklist_response_id) {
    return (
      <>
        {notStartedNotice}
        <NoResponseView wo={wo} canStart={canEdit} onStart={refetch} />
      </>
    )
  }

  return (
    <>
      {notStartedNotice}
      <ChecklistResponseView
        responseId={wo.checklist_response_id}
        workOrderId={wo.id}
        canEdit={canEdit}
        onComplete={refetch}
      />
    </>
  )
}

function NoResponseView({ wo, canStart, onStart }) {
  const createMut = useCreateChecklistResponse()

  const [startError, setStartError] = useState('')

  async function handleStart() {
    setStartError('')
    try {
      await createMut.mutateAsync({
        work_order: wo.id,
        version: wo.checklist_version.id,
      })
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
        <p className="font-medium text-gray-700">{wo.checklist_version.template_name}</p>
        <p className="text-sm text-gray-500">Versión v{wo.checklist_version.version_number}</p>
      </div>
      {canStart ? (
        <button
          onClick={handleStart}
          disabled={createMut.isPending}
          className="px-5 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60 transition-colors"
        >
          {createMut.isPending ? 'Iniciando...' : 'Iniciar checklist'}
        </button>
      ) : (
        <p className="text-xs text-gray-500">
          {wo.assigned_to
            ? 'Solo el técnico asignado puede iniciar el checklist.'
            : 'Asigna un técnico a esta OT para iniciar el checklist.'}
        </p>
      )}
      {startError && <p className="text-sm text-red-600">{startError}</p>}
    </div>
  )
}

function ChecklistResponseView({ responseId, workOrderId, canEdit, onComplete }) {
  const { data: response, isLoading, refetch } = useChecklistResponse(responseId)

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner small />
      </div>
    )
  }
  if (!response) return null

  if (response.completed_at) {
    return <CompletedChecklistView response={response} />
  }

  return (
    <ActiveChecklistForm
      response={response}
      workOrderId={workOrderId}
      canEdit={canEdit}
      onFieldSaved={refetch}
      onComplete={() => {
        refetch()
        onComplete()
      }}
    />
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

  const answeredMap = Object.fromEntries(fieldResponses.map((fr) => [fr.field, fr]))

  const groups = groupFields(allFields)
  const [groupIdx, setGroupIdx] = useState(0)
  const currentGroup = groups[groupIdx] ?? { name: '', fields: [] }

  const [localValues, setLocalValues] = useState(() => {
    const init = {}
    fieldResponses.forEach((fr) => { init[fr.field] = fr.value })
    return init
  })

  const submitFieldMut = useSubmitField(response.id)
  const completeMut = useCompleteChecklist(response.id)

  const isOnline = useNetworkStore((s) => s.isOnline)
  const refreshPendingCount = useNetworkStore((s) => s.refreshPendingCount)

  // Cachear el checklist en SQLite: sin esta fila el tecnico no puede abrirlo
  // sin red, y el indicador de pendientes no sabria a que OT pertenece.
  useEffect(() => {
    saveChecklistResponse({ ...response, work_order: workOrderId }).catch((error) =>
      console.warn('[Checklist] no se pudo cachear la respuesta:', error?.message ?? error)
    )
  }, [response, workOrderId])

  const answeredCount = fieldResponses.length
  const totalCount = allFields.length
  const requiredUnanswered = allFields.filter(
    (f) => f.is_required && !answeredMap[f.id]
  )
  const canComplete = requiredUnanswered.length === 0
  const isLastGroup = groupIdx === groups.length - 1

  /** Campos escritos que aun no llegaron al servidor (nadie disparo el blur). */
  function pendingFieldIds() {
    return Object.keys(localValues).filter(
      (id) => (localValues[id] ?? '') !== (answeredMap[id]?.value ?? '')
    )
  }

  async function handleBlur(fieldId) {
    if (!canEdit) return
    const value = localValues[fieldId] ?? ''
    if (answeredMap[fieldId]?.value === value) return

    // Siempre a SQLite primero: es la unica escritura que no puede fallar.
    await saveFieldResponse({
      id: newId(),
      response_id: response.id,
      field_id: fieldId,
      value,
      notes: '',
      answered_at: new Date().toISOString(),
      synced: 0,
    })

    if (!isOnline) {
      await refreshPendingCount()
      return
    }

    try {
      await submitFieldMut.mutateAsync({ field: fieldId, value, notes: '' })
      await markFieldResponseSynced(response.id, fieldId)
      onFieldSaved()
    } catch (err) {
      // Un fallo de red no interrumpe al tecnico: queda en cola.
      console.warn(
        '[Checklist] submit-field fallo, guardado offline:',
        err?.response?.data ?? err?.message
      )
    }
    await refreshPendingCount()
  }

  const [completeError, setCompleteError] = useState('')

  async function handleComplete() {
    if (!canComplete) return
    setCompleteError('')
    try {
      // Volcar primero lo que sigue solo en el formulario.
      for (const fieldId of pendingFieldIds()) {
        await handleBlur(fieldId)
      }
      await completeMut.mutateAsync()
      onComplete()
    } catch (err) {
      const data = err?.response?.data
      setCompleteError(
        data?.detail ?? 'No se pudo finalizar el checklist. Revisa los campos e intenta de nuevo.'
      )
    }
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
            </button>
          ))}
        </div>
      )}

      {/* Fields */}
      <div className="space-y-5">
        {currentGroup.fields.map((field) => (
          <ChecklistFieldInput
            key={field.id}
            field={field}
            workOrderId={workOrderId}
            value={localValues[field.id] ?? ''}
            fieldResponse={answeredMap[field.id]}
            disabled={!canEdit}
            onChange={(val) =>
              setLocalValues((prev) => ({ ...prev, [field.id]: val }))
            }
            onBlur={() => handleBlur(field.id)}
          />
        ))}
      </div>

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

function ChecklistFieldInput({ field, workOrderId, value, fieldResponse, disabled, onChange, onBlur }) {
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
  function setMultiValues(arr) { onChange(JSON.stringify(arr)) }

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
              onClick={() => { onChange(v); setTimeout(onBlur, 0) }}
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
                    setMultiValues(next)
                    setTimeout(onBlur, 0)
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
                    onChange(v)
                    setTimeout(onBlur, 0)
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
          value={value}
          disabled={disabled}
          onChange={onChange}
          onBlur={onBlur}
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
 * Antes solo guardaba `file.name` y mostraba "Foto adjuntada": el archivo no
 * salia del navegador. Ahora sube la imagen a la evidencia de la OT y guarda
 * la URL devuelta como valor del campo.
 */
function ChecklistPhotoField({ workOrderId, value, disabled, onChange, onBlur }) {
  const uploadPhoto = useUploadPhoto()
  const [error, setError] = useState('')

  async function handleFile(event) {
    const file = event.target.files?.[0]
    // Permite volver a elegir el mismo archivo despues de un fallo.
    event.target.value = ''
    if (!file) return

    setError('')
    try {
      const photo = await uploadPhoto.mutateAsync({
        work_order: workOrderId,
        file,
        taken_at: new Date().toISOString(),
        caption: 'Checklist',
      })
      onChange(photo.file_url ?? photo.id)
      setTimeout(onBlur, 0)
    } catch (err) {
      const detail = err?.response?.data
      const first = detail && typeof detail === 'object' ? Object.values(detail).flat()[0] : detail
      setError(String(first ?? 'No se pudo subir la foto.'))
    }
  }

  return (
    <div>
      {value && !uploadPhoto.isPending && (
        <p className="text-xs text-green-600 mb-1 flex items-center gap-1">
          <Icon name="camera" className="w-3.5 h-3.5 flex-shrink-0" />
          Foto adjunta
          <a
            href={value}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand hover:underline"
          >
            ver
          </a>
        </p>
      )}
      {!disabled && (
        <label
          className={`inline-flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg text-sm transition-colors ${
            uploadPhoto.isPending
              ? 'text-gray-400 cursor-wait'
              : 'text-gray-600 hover:bg-gray-50 cursor-pointer'
          }`}
        >
          {uploadPhoto.isPending ? <Spinner small /> : <Icon name="camera" className="w-4 h-4" />}
          {uploadPhoto.isPending ? 'Subiendo...' : 'Seleccionar foto'}
          <input
            type="file"
            accept="image/*"
            className="sr-only"
            disabled={uploadPhoto.isPending}
            onChange={handleFile}
          />
        </label>
      )}
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

function ReportsTab({ workOrderId, woStatus, role }) {
  const { data: reports = [], isLoading, isError, refetch } = useWorkOrderReports(workOrderId)
  const downloadMut = useReportDownload()
  const resendMut = useResendReportEmail()
  const [confirmResend, setConfirmResend] = useState(null)
  const [gaveUp, setGaveUp] = useState(false)
  const regenerateMut = useRegenerateReport(workOrderId)

  const hasReport = reports.length > 0

  // Temporizador explicito. Antes se comparaba contra `dataUpdatedAt`, pero ese
  // valor se refresca en cada sondeo, asi que el umbral no se alcanzaba nunca y
  // la pestaña se quedaba girando para siempre.
  useEffect(() => {
    if (woStatus !== 'COMPLETED' || hasReport) {
      setGaveUp(false)
      return undefined
    }
    const timer = setTimeout(() => setGaveUp(true), REPORT_POLL_TIMEOUT_MS)
    return () => clearTimeout(timer)
  }, [woStatus, hasReport])

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
  const answeredMap = Object.fromEntries(fieldResponses.map((fr) => [fr.field, fr]))
  const groups = groupFields(allFields)

  return (
    <div className="space-y-6">
      {/* Summary banner */}
      <div className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-xl p-4">
        <Icon name="checkCircle" className="w-7 h-7 flex-shrink-0 text-green-600" />
        <div>
          <p className="text-sm font-semibold text-green-800">Checklist completado</p>
          <p className="text-xs text-green-600">
            Inicio: {new Date(response.started_at).toLocaleString('es-CO')}
            {' · '}
            Cierre: {new Date(response.completed_at).toLocaleString('es-CO')}
          </p>
        </div>
      </div>

      {/* Read-only answers */}
      {groups.map((group, gi) => (
        <div key={gi} className="space-y-4">
          {group.name && (
            <h3 className="text-xs font-semibold text-gray-500 border-b border-gray-200 pb-2">
              {group.name}
            </h3>
          )}
          {group.fields.map((field) => {
            const fr = answeredMap[field.id]
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
                  {fr?.value || <span className="text-gray-500 italic">Sin respuesta</span>}
                </div>
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}
