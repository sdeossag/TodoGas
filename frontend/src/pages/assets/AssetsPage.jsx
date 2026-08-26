import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import { useHospitals, useAssetTree, useAssets } from '../../api/assets'
import Icon from '../../components/ui/Icon'

const STATUS_LABELS = {
  ACTIVE: { label: 'Activo', cls: 'bg-green-100 text-green-700' },
  OUT_OF_SERVICE: { label: 'Fuera de servicio', cls: 'bg-yellow-100 text-yellow-700' },
  DECOMMISSIONED: { label: 'Dado de baja', cls: 'bg-gray-100 text-gray-500' },
}

const PRIORITY_LABELS = {
  HIGH: { label: 'Alta', cls: 'text-red-600 font-semibold' },
  MEDIUM: { label: 'Media', cls: 'text-yellow-600' },
  LOW: { label: 'Baja', cls: 'text-gray-500' },
}

const PM_DOT = {
  on_time:  { cls: 'bg-green-500',  title: 'Mantenimiento al día' },
  due_soon: { cls: 'bg-yellow-400', title: 'Próximo mantenimiento en ≤15 días' },
  overdue:  { cls: 'bg-red-500',    title: 'Mantenimiento vencido' },
  no_plan:  { cls: 'bg-gray-300',   title: 'Sin plan de mantenimiento' },
}

function PmDot({ status }) {
  const dot = PM_DOT[status] ?? PM_DOT.no_plan
  return (
    <span
      title={dot.title}
      className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${dot.cls}`}
    />
  )
}

export default function AssetsPage() {
  const { user } = useAuthStore()
  const isAdminOrSup = ['ADMIN', 'SUP'].includes(user?.role)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [selectedHospitalId, setSelectedHospitalId] = useState(
    searchParams.get('hospital_id') ?? null
  )
  const [selectedNodeId, setSelectedNodeId] = useState(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  // Filtro de estado de mantenimiento — llega desde las tarjetas del dashboard.
  // El backend lo expone como campo calculado, asi que se filtra en cliente.
  const [pmFilter, setPmFilter] = useState(searchParams.get('maintenance_status') ?? '')
  const [searchInput, setSearchInput] = useState('')

  const { data: hospitals = [] } = useHospitals({ is_active: true })
  const { data: tree = [], isLoading: treeLoading } = useAssetTree(selectedHospitalId)

  const assetParams = {
    ...(selectedHospitalId && { hospital_id: selectedHospitalId }),
    ...(selectedNodeId && { node_id: selectedNodeId }),
    ...(search && { search }),
    ...(statusFilter && { status: statusFilter }),
  }
  const { data: allAssets = [], isLoading: assetsLoading } = useAssets(assetParams)
  const assets = pmFilter
    ? allAssets.filter((a) => (a.maintenance_status ?? 'no_plan') === pmFilter)
    : allAssets

  useEffect(() => {
    if (!selectedHospitalId && hospitals.length > 0) {
      setSelectedHospitalId(hospitals[0].id)
    }
  }, [hospitals, selectedHospitalId])

  function handleSearchSubmit(e) {
    e.preventDefault()
    setSearch(searchInput)
  }

  function handleHospitalChange(id) {
    setSelectedHospitalId(id)
    setSelectedNodeId(null)
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Activos</h1>
          <p className="text-sm text-gray-500 mt-0.5">Equipos médicos registrados</p>
        </div>
        {isAdminOrSup && (
          <button onClick={() => navigate('/activos/nuevo')}
            className="px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light transition-colors">
            + Nuevo activo
          </button>
        )}
      </div>

      {/* Dos columnas */}
      <div className="flex gap-4 h-[calc(100vh-200px)]">
        {/* Columna izquierda — árbol */}
        <div className="w-72 flex-shrink-0 bg-white rounded-xl border border-gray-100 shadow-sm flex flex-col">
          <div className="p-3 border-b">
            <select
              value={selectedHospitalId ?? ''}
              onChange={(e) => handleHospitalChange(e.target.value || null)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
            >
              <option value="">Seleccionar hospital</option>
              {hospitals.map((h) => (
                <option key={h.id} value={h.id}>{h.name}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {!selectedHospitalId ? (
              <p className="text-xs text-gray-500 text-center mt-6">Selecciona un hospital</p>
            ) : treeLoading ? (
              <div className="flex justify-center mt-6"><Spinner className="w-5 h-5 text-brand" /></div>
            ) : tree.length === 0 ? (
              <p className="text-xs text-gray-500 text-center mt-6">Sin ubicaciones registradas</p>
            ) : (
              <>
                <button
                  onClick={() => setSelectedNodeId(null)}
                  className={`w-full text-left px-2 py-1.5 rounded text-sm flex items-center gap-2 mb-1
                    ${!selectedNodeId ? 'bg-brand/10 text-brand font-medium' : 'text-gray-600 hover:bg-gray-50'}`}>
                  <Icon name="hospital" className="w-4 h-4 flex-shrink-0" /> Todos los activos
                </button>
                {tree.map((node) => (
                  <TreeNode key={node.id} node={node} selected={selectedNodeId}
                    onSelect={setSelectedNodeId} level={0} />
                ))}
              </>
            )}
          </div>
        </div>

        {/* Columna derecha — listado */}
        <div className="flex-1 bg-white rounded-xl border border-gray-100 shadow-sm flex flex-col overflow-hidden">
          {/* Barra de filtros */}
          <div className="p-3 border-b flex flex-wrap gap-2 items-center">
            <form onSubmit={handleSearchSubmit} className="flex gap-1">
              <input
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Buscar código, nombre, serial..."
                className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 w-56"
              />
              <button type="submit"
                className="px-3 py-1.5 bg-brand text-white text-sm rounded-lg hover:bg-brand-light">
                Buscar
              </button>
              {search && (
                <button type="button" onClick={() => { setSearch(''); setSearchInput('') }}
                  className="px-2 py-1.5 text-gray-500 hover:text-gray-600">
                  <Icon name="close" className="w-4 h-4" />
                </button>
              )}
            </form>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none">
              <option value="">Todos los estados</option>
              <option value="ACTIVE">Activo</option>
              <option value="OUT_OF_SERVICE">Fuera de servicio</option>
              <option value="DECOMMISSIONED">Dado de baja</option>
            </select>
            {pmFilter && (
              <button
                type="button"
                onClick={() => setPmFilter('')}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-brand-50 text-brand-800 text-xs font-medium hover:bg-brand-100"
              >
                <PmDot status={pmFilter} />
                {PM_DOT[pmFilter]?.title ?? pmFilter}
                <Icon name="close" className="w-3.5 h-3.5 text-gray-500" />
              </button>
            )}
          </div>

          {/* Tabla */}
          <div className="flex-1 overflow-y-auto">
            {assetsLoading ? (
              <div className="flex justify-center py-16"><Spinner className="w-8 h-8 text-brand" /></div>
            ) : assets.length === 0 ? (
              <div className="text-center py-16 text-gray-500">
                <Icon name="asset" className="w-10 h-10 mx-auto mb-3 text-gray-400" />
                <p className="font-medium">No hay activos en esta ubicación</p>
                {isAdminOrSup && (
                  <button onClick={() => navigate('/activos/nuevo')}
                    className="mt-3 text-sm text-brand hover:underline">
                    + Crear el primer activo
                  </button>
                )}
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-gray-50">
                  <tr className="text-left text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-4 py-3">Código</th>
                    <th className="px-4 py-3">Nombre</th>
                    <th className="px-4 py-3">Tipo</th>
                    <th className="px-4 py-3">Estado</th>
                    <th className="px-4 py-3">Prioridad</th>
                    <th className="px-4 py-3">Próximo PM</th>
                    <th className="px-4 py-3 text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {assets.map((a) => {
                    const st = STATUS_LABELS[a.status] ?? { label: a.status, cls: 'bg-gray-100 text-gray-500' }
                    const pr = PRIORITY_LABELS[a.priority] ?? { label: a.priority, cls: '' }
                    return (
                      <tr key={a.id} className="hover:bg-gray-50 transition-colors cursor-pointer"
                        onClick={() => navigate(`/activos/${a.id}`)}>
                        <td className="px-4 py-3 font-mono text-xs text-gray-500">{a.code}</td>
                        <td className="px-4 py-3 font-medium text-gray-800">
                          <div className="flex items-center gap-2">
                            <PmDot status={a.maintenance_status} />
                            {a.name}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-gray-500">{a.asset_type || '—'}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${st.cls}`}>
                            {st.label}
                          </span>
                        </td>
                        <td className={`px-4 py-3 text-xs ${pr.cls}`}>{pr.label}</td>
                        <td className="px-4 py-3 text-xs text-gray-500">
                          {a.next_maintenance_date
                            ? new Date(a.next_maintenance_date + 'T00:00:00').toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' })
                            : <span className="text-gray-500">Sin plan</span>}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={(e) => { e.stopPropagation(); navigate(`/activos/${a.id}`) }}
                            className="text-xs px-2 py-1 rounded bg-brand/10 text-brand hover:bg-brand/20">
                            Ver ficha
                          </button>
                          {isAdminOrSup && (
                            <button
                              onClick={(e) => { e.stopPropagation(); navigate(`/activos/${a.id}/editar`) }}
                              className="ml-1 text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200">
                              Editar
                            </button>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function TreeNode({ node, selected, onSelect, level }) {
  const [open, setOpen] = useState(level === 0)
  const hasChildren = node.children?.length > 0
  const isSelected = selected === node.id

  return (
    <div>
      <div
        className={`flex items-center gap-1 px-2 py-1 rounded text-sm cursor-pointer select-none
          ${isSelected ? 'bg-brand/10 text-brand font-medium' : 'text-gray-600 hover:bg-gray-50'}`}
        style={{ paddingLeft: `${8 + level * 14}px` }}
        onClick={() => onSelect(node.id)}
      >
        {hasChildren ? (
          <button onClick={(e) => { e.stopPropagation(); setOpen((o) => !o) }}
            className="w-4 text-center text-gray-500 hover:text-gray-600 flex-shrink-0">
            {open ? '▾' : '▸'}
          </button>
        ) : (
          <span className="w-4 flex-shrink-0" />
        )}
        <Icon name={nodeIcon(node.node_type)} className="w-4 h-4 text-gray-500 flex-shrink-0" />
        <span className="truncate">{node.name}</span>
      </div>
      {hasChildren && open && (
        <div>
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} selected={selected}
              onSelect={onSelect} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

function nodeIcon(type) {
  const icons = { BUILDING: 'building', FLOOR: 'floor', AREA: 'area', ROOM: 'room', OTHER: 'folder' }
  return icons[type] ?? 'folder'
}

function Spinner({ className = 'w-4 h-4 text-white' }) {
  return (
    <svg className={`animate-spin ${className}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}
