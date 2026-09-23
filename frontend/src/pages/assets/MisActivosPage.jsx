import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAssets } from '../../api/assets'
import { ASSET_STATUS_COLORS, assetStatusLabel } from '../../constants/labels'
import EmptyState from '../../components/ui/EmptyState'

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
                      <Link to={`/mis-activos/${asset.id}`} className="text-xs text-brand hover:underline">
                        Ver historial
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  )
}
