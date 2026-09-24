/**
 * Etiquetas en español de los valores de enumeracion del backend.
 *
 * Todo lo que llega de la API viene en ingles (ACTIVE, IN_PROGRESS, ...). Esta
 * es la unica traduccion: ninguna pantalla debe imprimir el valor crudo, porque
 * el cliente lo ve tal cual.
 */

export const ASSET_STATUS_LABELS = {
  ACTIVE: 'Activo',
  OUT_OF_SERVICE: 'Fuera de servicio',
  DECOMMISSIONED: 'Dado de baja',
}

export const ASSET_STATUS_COLORS = {
  ACTIVE: 'bg-green-100 text-green-700',
  OUT_OF_SERVICE: 'bg-yellow-100 text-yellow-700',
  DECOMMISSIONED: 'bg-gray-100 text-gray-500',
}

export const WO_STATUS_LABELS = {
  PENDING: 'Pendiente',
  IN_PROGRESS: 'En proceso',
  IN_REVIEW: 'En revisión',
  COMPLETED: 'Finalizada',
  CANCELLED: 'Cancelada',
}

export const WO_STATUS_COLORS = {
  PENDING: 'bg-gray-100 text-gray-600',
  IN_PROGRESS: 'bg-blue-100 text-blue-700',
  IN_REVIEW: 'bg-amber-100 text-amber-700',
  COMPLETED: 'bg-green-100 text-green-700',
  CANCELLED: 'bg-red-100 text-red-600',
}

export const TASK_TYPE_LABELS = {
  PREVENTIVE: 'Preventivo',
  CORRECTIVE: 'Correctivo',
  VERIFICATION: 'Verificación',
  INSTALLATION: 'Instalación',
  DELIVERY: 'Entrega',
}

/** Entidades del log de auditoria, tal como las nombra el backend. */
export const ENTITY_TYPE_LABELS = {
  WorkOrder: 'Orden de trabajo',
  Asset: 'Activo',
  Hospital: 'Hospital',
  Contract: 'Contrato o garantía',
  User: 'Usuario',
  Photo: 'Foto',
  Signature: 'Firma',
  ChecklistTemplate: 'Plantilla de checklist',
  ChecklistResponse: 'Respuesta de checklist',
  AssetCustomField: 'Campo personalizado',
  MaintenancePlan: 'Protocolo',
  PlanTask: 'Tarea del protocolo',
  Task: 'Tarea',
  RescheduleCause: 'Causa de reprogramación',
  InventoryItem: 'Item de inventario',
  StockMovement: 'Movimiento de stock',
  GeneratedReport: 'Acta',
  ReportSettings: 'Configuración del acta',
  // Inicios y cierres de sesion, refresco de token y cambio de contrasena.
  Authentication: 'Autenticacion',
}

/** Nombres de campo que el backend devuelve dentro de un error 400. */
export const FIELD_LABELS = {
  asset: 'Activo',
  asset_ids: 'Activos',
  cause_id: 'Causa',
  checklist_template: 'Checklist',
  frequency_unit: 'Unidad de frecuencia',
  frequency_value: 'Frecuencia',
  location: 'Ubicación',
  plan: 'Protocolo',
  repeat_count: 'Repetir',
  start_date: 'Primera vez',
  task_ids: 'Tareas',
  trigger: 'Activador',
  assigned_to: 'Técnico asignado',
  checklist_version: 'Checklist',
  code: 'Código',
  description: 'Descripción',
  email: 'Correo electrónico',
  estimated_duration: 'Duración estimada',
  hospital: 'Hospital',
  name: 'Nombre',
  node: 'Ubicación',
  notes: 'Notas',
  priority: 'Prioridad',
  request_number: 'Número de solicitud',
  role: 'Rol',
  scheduled_date: 'Fecha límite',
  status: 'Estado',
  task_type: 'Tipo de OT',
  title: 'Título',
  non_field_errors: 'Error',
  detail: 'Error',
}

export const assetStatusLabel = (value) => ASSET_STATUS_LABELS[value] ?? value ?? '—'
export const woStatusLabel = (value) => WO_STATUS_LABELS[value] ?? value ?? '—'
// Nombres del catálogo de tipos de tarea: los guarda useTaskTypes y quedan en
// el navegador para verlos sin red. Sin catálogo aún, el código se lee legible
// ("CAMBIO_DE_FILTROS" → "Cambio de filtros").
const TASK_TYPE_KEY = 'task_type_labels'
let taskTypeNames = (() => {
  try {
    return JSON.parse(localStorage.getItem(TASK_TYPE_KEY) ?? '{}') ?? {}
  } catch {
    return {}
  }
})()

export function rememberTaskTypeLabels(tipos) {
  taskTypeNames = { ...taskTypeNames, ...Object.fromEntries(tipos.map((t) => [t.code, t.name])) }
  try {
    localStorage.setItem(TASK_TYPE_KEY, JSON.stringify(taskTypeNames))
  } catch {
    // Sin almacenamiento solo se pierde el nombre guardado; queda el código legible.
  }
}

function legible(code) {
  const texto = code.replace(/_/g, ' ').toLowerCase()
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}

export const taskTypeLabel = (value) =>
  value ? (taskTypeNames[value] ?? TASK_TYPE_LABELS[value] ?? legible(value)) : '—'
export const entityTypeLabel = (value) => ENTITY_TYPE_LABELS[value] ?? value ?? '—'
export const fieldLabel = (value) => FIELD_LABELS[value] ?? value
