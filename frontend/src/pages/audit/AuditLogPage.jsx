import { useState } from 'react'
import useAuthStore from '../../store/authStore'
import { useAuditLog } from '../../api/audit'
import { useUsers } from '../../api/users'

const ACTION_LABELS = {
  CREATE: 'Crear',
  UPDATE: 'Actualizar',
  DELETE: 'Eliminar',
  STATUS_CHANGE: 'Cambio estado',
  LOGIN: 'Inicio sesion',
  SYNC: 'Sincronizacion',
}
const ACTION_COLORS = {
  CREATE: 'bg-green-100 text-green-700',
  UPDATE: 'bg-blue-100 text-blue-700',
  DELETE: 'bg-red-100 text-red-600',
  STATUS_CHANGE: 'bg-amber-100 text-amber-700',
  LOGIN: 'bg-gray-100 text-gray-600',
  SYNC: 'bg-gray-100 text-gray-600',
}

const ENTITY_TYPES = [
  'Asset', 'Hospital', 'WorkOrder', 'ChecklistTemplate',
  'MaintenancePlan', 'Photo', 'Signature', 'User',
  'InventoryItem', 'StockMovement',
]

function Spinner({ small }) {
  return (
    <svg className={`animate-spin ${small ? 'h-4 w-4' : 'h-8 w-8'} text-brand`} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

export default function AuditLogPage() {
  const { user } = useAuthStore()
  const [filters, setFilters] = useState({})
  const [page, setPage] = useState(1)

  const { data: usersData = [] } = useUsers({})
  const activeFilters = { ...filters, page }
  const { data, isLoading } = useAuditLog(activeFilters)

  const results = data?.results ?? []
  const count = data?.count ?? 0
  const totalPages = Math.max(1, Math.ceil(count / 50))

  function handleFilter(k, v) {
    setPage(1)
    setFilters((f) => {
      const next = { ...f }
      if (v) next[k] = v
      else delete next[k]
      return next
    })
  }

  function exportCsv() {
    const header = ['Fecha', 'Usuario', 'Accion', 'Tipo de entidad', 'ID entidad', 'IP']
    const rows = results.map((l) => [
      new Date(l.timestamp).toLocaleString('es-CO'),
      l.user?.full_name || '',
      ACTION_LABELS[l.action] || l.action,
      l.entity_type,
      l.entity_id,
      l.ip_address || '',
    ])
    const csv = [header, ...rows]
      .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(','))
      .join('\n')
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `auditoria-pagina-${page}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  if (user?.role !== 'ADMIN') {
    return (
      <div className="text-center py-20 text-gray-500">
        <p className="text-sm">No tienes permisos para ver el log de auditoria.</p>
      </div>
    )
  }

  const sel = 'border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none'

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Log de auditoria</h1>
          <p className="text-sm text-gray-500 mt-0.5">{count} registros totales</p>
        </div>
        <button
          onClick={exportCsv}
          disabled={results.length === 0}
          className="px-4 py-2 border border-gray-200 text-sm text-gray-600 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition-colors"
        >
          Exportar CSV (pagina actual)
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
        <div className="flex flex-wrap gap-3 items-center">
          <select
            value={filters.user_id || ''}
            onChange={(e) => handleFilter('user_id', e.target.value)}
            className={sel}
          >
            <option value="">Todos los usuarios</option>
            {usersData.map((u) => (
              <option key={u.id} value={u.id}>
                {u.first_name} {u.last_name}
              </option>
            ))}
          </select>

          <select
            value={filters.action || ''}
            onChange={(e) => handleFilter('action', e.target.value)}
            className={sel}
          >
            <option value="">Todas las acciones</option>
            {Object.entries(ACTION_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>

          <select
            value={filters.entity_type || ''}
            onChange={(e) => handleFilter('entity_type', e.target.value)}
            className={sel}
          >
            <option value="">Todos los tipos</option>
            {ENTITY_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>

          <div className="flex items-center gap-1">
            <label className="text-xs text-gray-500">Desde</label>
            <input
              type="date"
              value={filters.date_from || ''}
              onChange={(e) => handleFilter('date_from', e.target.value)}
              className={sel}
            />
          </div>

          <div className="flex items-center gap-1">
            <label className="text-xs text-gray-500">Hasta</label>
            <input
              type="date"
              value={filters.date_to || ''}
              onChange={(e) => handleFilter('date_to', e.target.value)}
              className={sel}
            />
          </div>

          <input
            type="text"
            placeholder="Buscar..."
            value={filters.search || ''}
            onChange={(e) => handleFilter('search', e.target.value)}
            className={`${sel} w-40`}
          />

          {Object.keys(filters).length > 0 && (
            <button
              onClick={() => { setFilters({}); setPage(1) }}
              className="text-xs text-gray-500 hover:text-gray-600"
            >
              Limpiar filtros
            </button>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : results.length === 0 ? (
          <div className="text-center py-16 text-gray-500 text-sm">Sin registros para los filtros seleccionados.</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr className="text-left text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-4 py-3">Fecha / Hora</th>
                    <th className="px-4 py-3">Usuario</th>
                    <th className="px-4 py-3">Accion</th>
                    <th className="px-4 py-3">Tipo de entidad</th>
                    <th className="px-4 py-3">Entidad ID</th>
                    <th className="px-4 py-3">IP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {results.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                        {new Date(log.timestamp).toLocaleString('es-CO')}
                      </td>
                      <td className="px-4 py-3 text-gray-700 text-xs">
                        {log.user?.full_name || <span className="text-gray-500">Sistema</span>}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 text-xs rounded-full font-medium ${ACTION_COLORS[log.action] ?? 'bg-gray-100 text-gray-500'}`}>
                          {ACTION_LABELS[log.action] || log.action}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-xs">{log.entity_type}</td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-500 truncate max-w-[120px]">
                        {log.entity_id}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{log.ip_address || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
              <span className="text-xs text-gray-500">
                Pagina {page} de {totalPages} ({count} registros)
              </span>
              <div className="flex gap-1">
                <button disabled={page === 1} onClick={() => setPage((p) => p - 1)}
                  className="px-3 py-1.5 text-xs rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50">
                  Anterior
                </button>
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const p = Math.max(1, Math.min(page - 2, totalPages - 4)) + i
                  return (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`px-3 py-1.5 text-xs rounded border ${p === page ? 'bg-brand text-white border-brand' : 'border-gray-200 hover:bg-gray-50'}`}
                    >
                      {p}
                    </button>
                  )
                })}
                <button disabled={page === totalPages} onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1.5 text-xs rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50">
                  Siguiente
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
