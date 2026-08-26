import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import { useAsset, useUpdateAsset, useDecommissionAsset } from '../../api/assets'
import Icon from '../../components/ui/Icon'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const STATUS_LABELS = {
  ACTIVE: { label: 'Activo', cls: 'bg-green-100 text-green-700' },
  OUT_OF_SERVICE: { label: 'Fuera de servicio', cls: 'bg-yellow-100 text-yellow-700' },
  DECOMMISSIONED: { label: 'Dado de baja', cls: 'bg-gray-100 text-gray-500' },
}

const PRIORITY_LABELS = {
  HIGH: { label: 'Alta', cls: 'bg-red-100 text-red-700' },
  MEDIUM: { label: 'Media', cls: 'bg-yellow-100 text-yellow-700' },
  LOW: { label: 'Baja', cls: 'bg-gray-100 text-gray-500' },
}

const TABS = ['Información general', 'Campos personalizados', 'Historial']

export default function AssetDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'ADMIN'
  const isAdminOrSup = ['ADMIN', 'SUP'].includes(user?.role)

  const [tab, setTab] = useState(0)
  const [confirmDecom, setConfirmDecom] = useState(false)

  const { data: asset, isLoading, isError } = useAsset(id)
  const decommissionMut = useDecommissionAsset(id)

  async function handleDecommission() {
    await decommissionMut.mutateAsync()
    setConfirmDecom(false)
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="w-10 h-10 text-brand" />
      </div>
    )
  }

  if (isError || !asset) {
    return (
      <div className="text-center py-20 text-gray-500">
        <Icon name="warning" className="w-10 h-10 mx-auto mb-3 text-amber-500" />
        <p>No se encontró el activo</p>
        <button onClick={() => navigate('/activos')} className="mt-3 text-sm text-brand hover:underline">
          Volver a activos
        </button>
      </div>
    )
  }

  const st = STATUS_LABELS[asset.status] ?? { label: asset.status, cls: 'bg-gray-100' }
  const pr = PRIORITY_LABELS[asset.priority] ?? { label: asset.priority, cls: 'bg-gray-100' }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 flex gap-1">
        <button onClick={() => navigate('/activos')} className="hover:text-brand">Activos</button>
        <span>/</span>
        <span className="text-gray-600">{asset.name}</span>
      </nav>

      {/* Encabezado */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${st.cls}`}>{st.label}</span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${pr.cls}`}>
                Prioridad {pr.label}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-gray-800 truncate">{asset.name}</h1>
            <p className="text-sm text-gray-500 font-mono mt-0.5">{asset.code}</p>
            {asset.node && (
              <p className="text-sm text-gray-500 mt-1 flex items-center gap-1.5">
            <Icon name="area" className="w-4 h-4 flex-shrink-0" />
            {asset.node.path}
          </p>
            )}
          </div>
          <div className="flex gap-2 flex-shrink-0">
            {isAdminOrSup && asset.status !== 'DECOMMISSIONED' && (
              <button onClick={() => navigate(`/activos/${id}/editar`)}
                className="px-4 py-2 bg-brand text-white text-sm rounded-lg hover:bg-brand-light">
                Editar
              </button>
            )}
            {isAdmin && asset.status !== 'DECOMMISSIONED' && (
              <button onClick={() => setConfirmDecom(true)}
                className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700">
                Dar de baja
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="border-b flex">
          {TABS.map((t, i) => (
            <button key={t} onClick={() => setTab(i)}
              className={`px-5 py-3 text-sm font-medium transition-colors
                ${tab === i
                  ? 'border-b-2 border-brand text-brand'
                  : 'text-gray-500 hover:text-gray-700'}`}>
              {t}
            </button>
          ))}
        </div>

        <div className="p-6">
          {tab === 0 && <InfoTab asset={asset} />}
          {tab === 1 && <CustomFieldsTab asset={asset} />}
          {tab === 2 && <HistoryTab />}
        </div>
      </div>

      {/* Modal confirmación baja */}
      {confirmDecom && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6 space-y-4">
            <h3 className="text-lg font-semibold text-gray-800">Confirmar baja del activo</h3>
            <p className="text-sm text-gray-600">
              Esta acción marca el activo como <strong>dado de baja</strong>. No podrá recibir nuevas
              órdenes de trabajo. El historial se conserva.
            </p>
            <p className="text-sm text-gray-600">¿Confirmar?</p>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setConfirmDecom(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
                Cancelar
              </button>
              <button onClick={handleDecommission} disabled={decommissionMut.isPending}
                className="px-5 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center gap-2">
                {decommissionMut.isPending && <Spinner />}
                Dar de baja
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const PM_STATUS_BADGE = {
  on_time:  { label: 'Al día',          cls: 'bg-green-100 text-green-700' },
  due_soon: { label: 'Próximo a vencer', cls: 'bg-yellow-100 text-yellow-700' },
  overdue:  { label: 'Vencido',          cls: 'bg-red-100 text-red-700' },
  no_plan:  { label: 'Sin plan',         cls: 'bg-gray-100 text-gray-500' },
}

function InfoTab({ asset }) {
  const token = localStorage.getItem('access_token')
  const pmBadge = PM_STATUS_BADGE[asset.maintenance_status] ?? PM_STATUS_BADGE.no_plan

  return (
    <div className="space-y-6">
      {/* Estado de mantenimiento */}
      <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
        <h3 className="text-sm font-semibold text-gray-600 mb-3">Estado de mantenimiento</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-0.5">Próximo mantenimiento</p>
            <p className="text-sm text-gray-800">
              {asset.next_maintenance_date
                ? new Date(asset.next_maintenance_date + 'T00:00:00').toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' })
                : <span className="text-gray-500">Sin plan</span>}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-0.5">Último mantenimiento</p>
            <p className="text-sm text-gray-800">
              {asset.last_maintenance_date
                ? new Date(asset.last_maintenance_date + 'T00:00:00').toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' })
                : <span className="text-gray-500">Nunca</span>}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-0.5">Estado</p>
            <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${pmBadge.cls}`}>
              {pmBadge.label}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-8 gap-y-4">
        <InfoField label="Hospital" value={asset.hospital?.name} />
        <InfoField label="Ubicación" value={asset.node?.path ?? '—'} />
        <InfoField label="Tipo de activo" value={asset.asset_type || '—'} />
        <InfoField label="Fabricante" value={asset.manufacturer || '—'} />
        <InfoField label="Modelo" value={asset.model || '—'} />
        <InfoField label="Número de serie" value={asset.serial_number || '—'} />
        <InfoField label="Proveedor" value={asset.supplier || '—'} />
        <InfoField label="Código de barras" value={asset.barcode || '—'} />
        <InfoField label="Fecha de compra" value={formatDate(asset.purchase_date)} />
        <InfoField label="Fecha de instalación" value={formatDate(asset.installation_date)} />
        <InfoField label="Garantía hasta" value={formatDate(asset.warranty_expiry)} />
        <InfoField label="Horas uso promedio/día" value={asset.avg_daily_usage_hours ?? '—'} />
        {asset.notes && (
          <div className="col-span-2">
            <InfoField label="Notas" value={asset.notes} />
          </div>
        )}
      </div>

      {/* QR */}
      <div className="border-t pt-6">
        <h3 className="text-sm font-semibold text-gray-600 mb-3">Código QR</h3>
        <div className="flex items-start gap-6">
          {asset.qr_code ? (
            <img src={asset.qr_code} alt="QR" className="w-32 h-32 border rounded-lg" />
          ) : (
            <div className="w-32 h-32 border-2 border-dashed border-gray-200 rounded-lg flex items-center justify-center text-gray-500 text-xs">
              Sin QR
            </div>
          )}
          <div className="space-y-2 pt-1">
            <p className="text-xs text-gray-500">
              Imprime y pega esta etiqueta en el equipo para acceso rápido.
            </p>
            <a
              href={`${BASE_URL}/api/assets/${asset.id}/qr-label/`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-brand text-white text-xs rounded-lg hover:bg-brand-light"
            >
              <Icon name="download" className="w-4 h-4" />
              Descargar etiqueta PNG
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

function CustomFieldsTab({ asset }) {
  const values = asset.custom_field_values ?? []
  if (values.length === 0) {
    return (
      <p className="text-sm text-gray-500 text-center py-8">
        Este tipo de activo no tiene campos personalizados.
      </p>
    )
  }
  return (
    <div className="grid grid-cols-2 gap-x-8 gap-y-4">
      {values.map((v) => (
        <InfoField key={v.id} label={v.field?.field_name ?? v.id} value={v.value || '—'} />
      ))}
    </div>
  )
}

function HistoryTab() {
  return (
    <div className="text-center py-12 text-gray-500">
      <Icon name="clock" className="w-10 h-10 mx-auto mb-3 text-gray-400" />
      <p className="font-medium">Historial disponible en próximos sprints</p>
      <p className="text-sm mt-1">El historial de órdenes de trabajo se implementará en Sprint 3.</p>
    </div>
  )
}

function InfoField({ label, value }) {
  return (
    <div>
      <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-0.5">{label}</p>
      <p className="text-sm text-gray-800">{value}</p>
    </div>
  )
}

function formatDate(val) {
  if (!val) return '—'
  return new Date(val).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' })
}

function Spinner({ className = 'w-4 h-4 text-white' }) {
  return (
    <svg className={`animate-spin ${className}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}
