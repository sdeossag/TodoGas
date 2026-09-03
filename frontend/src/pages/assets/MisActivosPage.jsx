import { useState } from 'react'
import { useAssets } from '../../api/assets'
import { useWorkOrders } from '../../api/workOrders'
import { useReportDownload } from '../../api/reports'
import { ASSET_STATUS_COLORS, assetStatusLabel } from '../../constants/labels'
import useModalDismiss from '../../hooks/useModalDismiss'
import EmptyState from '../../components/ui/EmptyState'
import { formatWoCode } from '../../utils/workOrder'

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

export default function MisActivosPage() {
  const [search, setSearch] = useState('')
  const [selectedAsset, setSelectedAsset] = useState(null)

  const { data: assets = [], isLoading, isError } = useAssets({})

  const filtered = assets.filter((a) => {
    const q = search.toLowerCase()
    return (
      a.name?.toLowerCase().includes(q) ||
      a.code?.toLowerCase().includes(q) ||
      a.manufacturer?.toLowerCase().includes(q) ||
      a.model?.toLowerCase().includes(q)
    )
  })

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900 mb-1">Mis activos</h1>
        <p className="text-sm text-gray-500">Equipos y dispositivos de su institucion</p>
      </div>

      {/* Search */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-card p-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nombre, codigo, marca o modelo..."
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
        />
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Spinner />
          </div>
        ) : isError ? (
          <div className="text-center py-16 text-red-600 text-sm">
            No se pudo cargar el listado de activos. Revisa tu conexion e intenta de nuevo.
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={search ? 'eye' : 'asset'}
            title={search ? 'Sin resultados' : 'Todavia no hay activos'}
            description={
              search
                ? `Ningun activo coincide con "${search}". Prueba con el codigo o con parte del nombre.`
                : 'Cuando el equipo registre los activos de tu sede apareceran en esta lista.'
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50 text-left">
                  <th className="px-4 py-3 text-xs font-semibold text-gray-500">Codigo</th>
                  <th className="px-4 py-3 text-xs font-semibold text-gray-500">Nombre</th>
                  <th className="px-4 py-3 text-xs font-semibold text-gray-500">Marca / Modelo</th>
                  <th className="px-4 py-3 text-xs font-semibold text-gray-500">Ubicacion</th>
                  <th className="px-4 py-3 text-xs font-semibold text-gray-500">Estado</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map((asset) => (
                  <tr key={asset.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-mono text-gray-600">{asset.code}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{asset.name}</td>
                    <td className="px-4 py-3 text-gray-500">
                      {[asset.manufacturer, asset.model].filter(Boolean).join(' / ') || '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {asset.node?.path || asset.equipment_location || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${ASSET_STATUS_COLORS[asset.status] ?? 'bg-gray-100 text-gray-500'}`}>
                        {assetStatusLabel(asset.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => setSelectedAsset(asset)}
                        className="text-xs text-brand hover:underline"
                      >
                        Ver OTs
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedAsset && (
        <AssetOTModal asset={selectedAsset} onClose={() => setSelectedAsset(null)} />
      )}
    </div>
  )
}

function AssetOTModal({ asset, onClose }) {
  useModalDismiss(onClose)
  const { data: workOrders = [], isLoading } = useWorkOrders({ asset_id: asset.id })
  const downloadMut = useReportDownload()

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-[2px] p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <div>
            <h3 className="font-semibold text-gray-800">{asset.name}</h3>
            <p className="text-xs text-gray-500 font-mono">{asset.code}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-600 text-xl leading-none"
          >
            ×
          </button>
        </div>

        <div className="overflow-y-auto flex-1 p-5">
          {isLoading ? (
            <div className="flex justify-center py-10">
              <Spinner />
            </div>
          ) : workOrders.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-10">
              No hay ordenes de trabajo completadas para este activo.
            </p>
          ) : (
            <div className="space-y-3">
              {workOrders.map((wo) => (
                <div
                  key={wo.id}
                  className="border border-gray-200 rounded-lg p-4 flex items-center justify-between gap-4 flex-wrap"
                >
                  <div className="space-y-0.5 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-sm font-semibold text-gray-600">
                        {formatWoCode(wo)}
                      </span>
                      <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full">
                        Completada
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 truncate">{wo.title}</p>
                    <p className="text-xs text-gray-500">{wo.scheduled_date}</p>
                  </div>
                  {wo.has_report && wo.report_id && (
                    <button
                      onClick={() => downloadMut.mutate(wo.report_id)}
                      disabled={downloadMut.isPending}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-brand text-white text-xs font-medium rounded-lg hover:bg-brand-light disabled:opacity-60 whitespace-nowrap"
                    >
                      {downloadMut.isPending ? <Spinner small /> : null}
                      Descargar PDF
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-100 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  )
}
