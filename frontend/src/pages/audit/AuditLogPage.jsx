import { Fragment, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import useAuthStore from '../../store/authStore'
import { useAuditLog } from '../../api/audit'
import { useUsers } from '../../api/users'
import { ENTITY_TYPE_LABELS, entityTypeLabel } from '../../constants/labels'
import Spinner from '../../components/ui/Spinner'
import EmptyState from '../../components/ui/EmptyState'

const PAGE_SIZE = 50

const ACTION_LABELS = {
  CREATE: 'Crear',
  UPDATE: 'Actualizar',
  DELETE: 'Eliminar',
  STATUS_CHANGE: 'Cambio de estado',
  LOGIN: 'Inicio de sesion',
  SYNC: 'Sincronizacion',
}
const ACTION_COLORS = {
  CREATE: 'bg-green-100 text-green-700',
  UPDATE: 'bg-blue-100 text-blue-700',
  DELETE: 'bg-red-100 text-red-600',
  STATUS_CHANGE: 'bg-amber-100 text-amber-700',
  LOGIN: 'bg-gray-100 text-gray-600',
  SYNC: 'bg-purple-100 text-purple-700',
}

// El valor se manda tal cual al backend; solo se traduce lo que se muestra.
const ENTITY_TYPES = Object.keys(ENTITY_TYPE_LABELS)

const EMPTY_FILTERS = {
  user_id: '',
  action: '',
  entity_type: '',
  date_from: '',
  date_to: '',
}


/** Quita las claves vacias: el backend filtra por presencia, no por valor. */
function compact(filters) {
  return Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== '' && v != null))
}

function formatValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'si' : 'no'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

/**
 * `changes` no tiene una forma unica en el backend: unas vistas guardan
 * escalares planos y otras pares {from, to}. Se soportan las dos, mas arrays
 * de dos elementos, y lo que no encaje se muestra tal cual.
 */
function ChangeRow({ field, value }) {
  let before = null
  let after = null

  if (Array.isArray(value) && value.length === 2) {
    ;[before, after] = value
  } else if (value && typeof value === 'object') {
    const keys = Object.keys(value)
    const fromKey = keys.find((k) => k === 'from' || k === 'old' || k === 'before')
    const toKey = keys.find((k) => k === 'to' || k === 'new' || k === 'after')
    if (fromKey || toKey) {
      before = value[fromKey]
      after = value[toKey]
    }
  }

  const isTransition = before !== null || after !== null

  return (
    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 py-1">
      <span className="text-xs font-medium text-gray-600">{field}:</span>
      {isTransition ? (
        <span className="text-xs text-gray-700">
          <span className="text-gray-500 line-through">{formatValue(before)}</span>
          <span className="mx-1.5 text-gray-400">→</span>
          <span className="font-medium">{formatValue(after)}</span>
        </span>
      ) : (
        <span className="text-xs text-gray-700 break-all">{formatValue(value)}</span>
      )}
    </div>
  )
}

function ChangesPanel({ changes }) {
  const entries = changes && typeof changes === 'object' ? Object.entries(changes) : []

  if (entries.length === 0) {
    return <p className="text-xs text-gray-500">Sin detalle de cambios</p>
  }
  return (
    <div className="divide-y divide-gray-100">
      {entries.map(([field, value]) => (
        <ChangeRow key={field} field={field} value={value} />
      ))}
    </div>
  )
}

export default function AuditLogPage() {
  const { user } = useAuthStore()
  const [searchParams, setSearchParams] = useSearchParams()

  // Filtros en edicion (draft) vs. los que estan aplicados a la consulta.
  const [draft, setDraft] = useState(EMPTY_FILTERS)
  const [applied, setApplied] = useState(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [expandedId, setExpandedId] = useState(null)

  // El enlace "Ver historial completo" del modal de usuarios llega con ?user_id=
  const urlUserId = searchParams.get('user_id') ?? ''
  useEffect(() => {
    if (urlUserId) {
      setDraft((d) => ({ ...d, user_id: urlUserId }))
      setApplied((a) => ({ ...a, user_id: urlUserId }))
      setPage(1)
    }
  }, [urlUserId])

  const { data: usersData } = useUsers()
  const users = useMemo(
    () => (Array.isArray(usersData) ? usersData : usersData?.results ?? []),
    [usersData]
  )

  const query = useMemo(() => ({ ...compact(applied), page }), [applied, page])
  const { data, isLoading, isError } = useAuditLog(query)

  const results = data?.results ?? []
  const count = data?.count ?? 0
  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE))

  const setField = (k) => (e) => setDraft((d) => ({ ...d, [k]: e.target.value }))

  function applyFilters() {
    setApplied(draft)
    setPage(1)
    setExpandedId(null)
    // La URL manda sobre el filtro de usuario: si se cambia, hay que soltarla.
    if (urlUserId && draft.user_id !== urlUserId) {
      searchParams.delete('user_id')
      setSearchParams(searchParams, { replace: true })
    }
  }

  function clearFilters() {
    setDraft(EMPTY_FILTERS)
    setApplied(EMPTY_FILTERS)
    setPage(1)
    setExpandedId(null)
    if (urlUserId) {
      searchParams.delete('user_id')
      setSearchParams(searchParams, { replace: true })
    }
  }

  function exportCsv() {
    const header = ['Fecha', 'Usuario', 'Accion', 'Entidad', 'ID entidad', 'IP']
    const rows = results.map((l) => [
      new Date(l.timestamp).toLocaleString('es-CO'),
      l.user?.full_name || 'Sistema',
      ACTION_LABELS[l.action] || l.action,
      entityTypeLabel(l.entity_type),
      l.entity_id,
      l.ip_address || '',
    ])
    const csv = [header, ...rows]
      .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(','))
      .join('\n')
    // BOM para que Excel en es-CO no rompa los acentos.
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
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

  const sel = 'border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30'

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Log de auditoria</h1>
          <p className="text-sm text-gray-500 mt-0.5">{count} registros</p>
        </div>
        <button
          onClick={exportCsv}
          disabled={results.length === 0}
          className="px-4 py-2 border border-gray-200 text-sm text-gray-600 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition-colors"
        >
          Exportar CSV (pagina actual)
        </button>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-card p-4">
        <div className="flex flex-wrap gap-3 items-center">
          <select value={draft.user_id} onChange={setField('user_id')} className={sel}>
            <option value="">Todos los usuarios</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.first_name} {u.last_name}
              </option>
            ))}
          </select>

          <select value={draft.action} onChange={setField('action')} className={sel}>
            <option value="">Todas las acciones</option>
            {Object.entries(ACTION_LABELS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>

          <select value={draft.entity_type} onChange={setField('entity_type')} className={sel}>
            <option value="">Todas las entidades</option>
            {ENTITY_TYPES.map((t) => (
              <option key={t} value={t}>
                {entityTypeLabel(t)}
              </option>
            ))}
          </select>

          <div className="flex items-center gap-1">
            <label className="text-xs text-gray-500">Desde</label>
            <input type="date" value={draft.date_from} onChange={setField('date_from')} className={sel} />
          </div>

          <div className="flex items-center gap-1">
            <label className="text-xs text-gray-500">Hasta</label>
            <input type="date" value={draft.date_to} onChange={setField('date_to')} className={sel} />
          </div>

          <div className="flex gap-2 ml-auto">
            <button
              type="button"
              onClick={applyFilters}
              className="px-4 py-1.5 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand/90 transition-colors"
            >
              Aplicar filtros
            </button>
            <button
              type="button"
              onClick={clearFilters}
              className="px-4 py-1.5 border border-gray-200 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors"
            >
              Limpiar
            </button>
          </div>
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Spinner />
          </div>
        ) : isError ? (
          <div className="text-center py-16 text-sm text-red-500">
            No se pudo cargar el log de auditoria.
          </div>
        ) : results.length === 0 ? (
          <EmptyState
            icon="audit"
            title="Sin registros para estos filtros"
            description="El log guarda cada creacion, cambio y borrado. Amplia el rango de fechas o quita el filtro de usuario."
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr className="text-left text-xs font-medium text-gray-500">
                    <th className="px-4 py-3">Fecha / Hora</th>
                    <th className="px-4 py-3">Usuario</th>
                    <th className="px-4 py-3">Accion</th>
                    <th className="px-4 py-3">Entidad</th>
                    <th className="px-4 py-3">ID</th>
                    <th className="px-4 py-3">IP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {results.map((log) => {
                    const expanded = expandedId === log.id
                    return (
                      <Fragment key={log.id}>
                        <tr
                          onClick={() => setExpandedId(expanded ? null : log.id)}
                          className={`cursor-pointer hover:bg-gray-50 ${expanded ? 'bg-gray-50' : ''}`}
                        >
                          <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                            {new Date(log.timestamp).toLocaleString('es-CO')}
                          </td>
                          <td className="px-4 py-3 text-gray-700 text-xs">
                            {log.user?.full_name || <span className="text-gray-500">Sistema</span>}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-flex px-2 py-0.5 text-xs rounded-full font-medium ${
                                ACTION_COLORS[log.action] ?? 'bg-gray-100 text-gray-500'
                              }`}
                            >
                              {ACTION_LABELS[log.action] || log.action}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-600 text-xs">{entityTypeLabel(log.entity_type)}</td>
                          <td className="px-4 py-3 font-mono text-xs text-gray-500">
                            {String(log.entity_id ?? '').slice(0, 8)}
                          </td>
                          <td className="px-4 py-3 text-gray-500 text-xs">{log.ip_address || '—'}</td>
                        </tr>
                        {expanded && (
                          <tr className="bg-gray-50">
                            <td colSpan={6} className="px-4 pb-4 pt-0">
                              <div className="rounded-lg border border-gray-200 bg-white p-3">
                                <p className="text-[11px] font-semibold text-gray-500 mb-2">
                                  Detalle de cambios
                                </p>
                                <ChangesPanel changes={log.changes} />
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
              <span className="text-xs text-gray-500">
                Pagina {page} de {totalPages} ({count} registros)
              </span>
              <div className="flex gap-1">
                <button
                  disabled={page === 1}
                  onClick={() => {
                    setPage((p) => p - 1)
                    setExpandedId(null)
                  }}
                  className="px-3 py-1.5 text-xs rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
                >
                  Anterior
                </button>
                <button
                  disabled={page >= totalPages}
                  onClick={() => {
                    setPage((p) => p + 1)
                    setExpandedId(null)
                  }}
                  className="px-3 py-1.5 text-xs rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
                >
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
