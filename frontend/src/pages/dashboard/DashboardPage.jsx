import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { useDashboard, useComplianceHistory, useAssetsStatus } from '../../api/dashboard'
import { useHospitals } from '../../api/assets'
import KpiCard from '../../components/dashboard/KpiCard'
import { complianceColor } from '../../components/dashboard/ComplianceBar'
import Table from '../../components/ui/Table'

const STATUS_COLORS = {
  PENDING: '#9ca3af',
  IN_PROGRESS: '#3b82f6',
  IN_REVIEW: '#f59e0b',
  COMPLETED: '#16a34a',
  CANCELLED: '#ef4444',
}

const STATUS_LABELS = {
  PENDING: 'Pendiente',
  IN_PROGRESS: 'En proceso',
  IN_REVIEW: 'En revision',
  COMPLETED: 'Finalizada',
  CANCELLED: 'Cancelada',
}

const MONTH_ABBR = [
  'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
  'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
]

const PERIODS = [
  { value: 7, label: '7 dias' },
  { value: 30, label: '30 dias' },
  { value: 90, label: '90 dias' },
]

const ASSET_STATUS_CARDS = [
  { key: 'on_time', label: 'Al dia', filter: 'on_time', color: 'text-green-600', dot: 'bg-green-500' },
  { key: 'due_soon', label: 'Proximo vencimiento', filter: 'due_soon', color: 'text-amber-600', dot: 'bg-amber-500' },
  { key: 'overdue', label: 'Vencido', filter: 'overdue', color: 'text-red-600', dot: 'bg-red-500' },
  { key: 'no_plan', label: 'Sin plan', filter: 'no_plan', color: 'text-gray-600', dot: 'bg-gray-400' },
]

function CardSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
      <div className="h-3 w-24 bg-gray-100 rounded animate-pulse" />
      <div className="mt-3 h-8 w-20 bg-gray-100 rounded animate-pulse" />
      <div className="mt-3 h-3 w-32 bg-gray-100 rounded animate-pulse" />
    </div>
  )
}

function ChartSkeleton({ title }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
      <div className="h-4 w-40 bg-gray-100 rounded animate-pulse" />
      <div className="mt-5 h-64 bg-gray-50 rounded-lg animate-pulse" aria-label={title} />
    </div>
  )
}

function Panel({ title, children }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-700">{title}</h2>
      </div>
      {children}
    </div>
  )
}

function StatusTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null
  const item = payload[0]
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-md px-3 py-2 text-xs">
      <p className="font-medium text-gray-700">{item.name}</p>
      <p className="text-gray-500">{item.value} orden(es)</p>
    </div>
  )
}

function ComplianceTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null
  const d = payload[0].payload
  if (d.percentage == null) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-md px-3 py-2 text-xs">
        <p className="font-medium text-gray-700">{d.label}</p>
        <p className="text-gray-500">Sin datos</p>
      </div>
    )
  }
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-md px-3 py-2 text-xs">
      <p className="font-medium text-gray-700">
        {d.label}: {d.percentage}%
      </p>
      <p className="text-gray-500">
        {d.completed} completadas / {d.generated} generadas
      </p>
    </div>
  )
}

export default function DashboardPage() {
  const queryClient = useQueryClient()

  const [hospitalId, setHospitalId] = useState('')
  const [days, setDays] = useState(30)

  const params = useMemo(() => {
    const p = { days }
    if (hospitalId) p.hospital_id = hospitalId
    return p
  }, [hospitalId, days])

  const historyParams = useMemo(
    () => (hospitalId ? { hospital_id: hospitalId, months: 12 } : { months: 12 }),
    [hospitalId]
  )
  const assetsParams = useMemo(
    () => (hospitalId ? { hospital_id: hospitalId } : {}),
    [hospitalId]
  )

  const { data: hospitals = [] } = useHospitals()
  const { data, isLoading, isFetching, error } = useDashboard(params)
  const { data: history = [], isLoading: historyLoading } = useComplianceHistory(historyParams)
  const { data: assetsStatus, isLoading: assetsLoading } = useAssetsStatus(assetsParams)

  const hospitalList = Array.isArray(hospitals) ? hospitals : hospitals?.results ?? []

  function goToAssets(maintenanceStatus) {
    const qs = new URLSearchParams({ maintenance_status: maintenanceStatus })
    if (hospitalId) qs.set('hospital_id', hospitalId)
    return `/activos?${qs.toString()}`
  }

  function handleRefresh() {
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  // ── Datos derivados ──────────────────────────────────────────────────────
  const compliance = data?.compliance
  const mttr = data?.mttr
  const overdue = data?.overdue
  const otsByStatus = data?.ots_by_status ?? {}
  const totalOts = Object.values(otsByStatus).reduce((a, b) => a + b, 0)

  const pieData = Object.entries(STATUS_COLORS)
    .map(([status, color]) => ({
      status,
      name: STATUS_LABELS[status],
      value: otsByStatus[status] ?? 0,
      color,
    }))
    .filter((d) => d.value > 0)

  // El backend devuelve month como "YYYY-MM"
  const historyData = (history ?? []).map((h) => {
    const [year, month] = (h.month ?? '').split('-')
    const idx = parseInt(month, 10) - 1
    const abbr = MONTH_ABBR[idx] ?? h.month
    return {
      label: year ? `${abbr} ${year}` : abbr,
      month: abbr,
      percentage: h.generated > 0 ? h.percentage : null,
      completed: h.completed,
      generated: h.generated,
    }
  })

  const technicians = [...(data?.ots_by_technician ?? [])].sort((a, b) => b.overdue - a.overdue)
  const assetsWithoutPm = (data?.assets_without_maintenance ?? []).slice(0, 10)

  const complianceColorName =
    compliance == null
      ? 'gray'
      : compliance.percentage >= 80
        ? 'green'
        : compliance.percentage >= 50
          ? 'yellow'
          : 'red'

  return (
    <div className="space-y-6">
      {/* Encabezado + filtros */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Indicadores de gestion de mantenimiento
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Hospital</label>
            <select
              value={hospitalId}
              onChange={(e) => setHospitalId(e.target.value)}
              className="input-field w-56 py-2"
            >
              <option value="">Todos los hospitales</option>
              {hospitalList.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">Periodo</label>
            <div className="inline-flex rounded-md border border-gray-300 overflow-hidden">
              {PERIODS.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  onClick={() => setDays(p.value)}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    days === p.value
                      ? 'bg-brand text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <button
            type="button"
            onClick={handleRefresh}
            className="btn-secondary"
            disabled={isFetching}
          >
            {isFetching ? 'Actualizando...' : 'Actualizar'}
          </button>
        </div>
      </div>

      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          No se pudieron cargar los indicadores. Intenta de nuevo.
        </div>
      )}

      {/* Fila 1 — KPIs principales */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          [...Array(4)].map((_, i) => <CardSkeleton key={i} />)
        ) : (
          <>
            <KpiCard
              title="Cumplimiento de planes"
              value={`${compliance?.percentage ?? 0}%`}
              subtitle={`${compliance?.completed ?? 0}/${compliance?.generated ?? 0} OTs`}
              color={complianceColorName}
            />
            <KpiCard
              title="MTTR (tiempo medio de reparacion)"
              value={`${(mttr?.mttr_hours ?? 0).toFixed(1)}h`}
              subtitle={`Basado en ${mttr?.sample_size ?? 0} OTs correctivas`}
              color="blue"
            />
            <KpiCard
              title="OTs vencidas"
              value={overdue?.count ?? 0}
              subtitle={`${overdue?.critical ?? 0} criticas (prioridad alta)`}
              color={(overdue?.count ?? 0) > 0 ? 'red' : 'green'}
            />
            <KpiCard
              title="OTs completadas este periodo"
              value={otsByStatus.COMPLETED ?? 0}
              subtitle={`De ${totalOts} ordenes en el periodo`}
              color="blue"
            />
          </>
        )}
      </div>

      {/* Fila 2 — Graficos principales */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {isLoading ? (
          <ChartSkeleton title="OTs por estado" />
        ) : (
          <Panel title="OTs por estado">
            <div className="p-5">
              {pieData.length === 0 ? (
                <div className="h-[260px] flex items-center justify-center text-sm text-gray-500">
                  Sin ordenes en el periodo seleccionado.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={65}
                      outerRadius={100}
                      paddingAngle={2}
                      stroke="#ffffff"
                      strokeWidth={2}
                      isAnimationActive={false}
                    >
                      {pieData.map((entry) => (
                        <Cell key={entry.status} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip content={<StatusTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              )}

              {/* Leyenda con conteos */}
              <ul className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2">
                {Object.entries(STATUS_COLORS).map(([status, color]) => (
                  <li key={status} className="flex items-center gap-2 text-sm">
                    <span
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-gray-600 flex-1">{STATUS_LABELS[status]}</span>
                    <span className="font-semibold text-gray-800 tabular-nums">
                      {otsByStatus[status] ?? 0}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </Panel>
        )}

        {historyLoading ? (
          <ChartSkeleton title="Cumplimiento ultimos 12 meses" />
        ) : (
          <Panel title="Cumplimiento — ultimos 12 meses">
            <div className="p-5">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={historyData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 12, fill: '#6b7280' }}
                    axisLine={{ stroke: '#e5e7eb' }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, 100]}
                    ticks={[0, 25, 50, 75, 100]}
                    tick={{ fontSize: 12, fill: '#6b7280' }}
                    axisLine={false}
                    tickLine={false}
                    unit="%"
                  />
                  <Tooltip content={<ComplianceTooltip />} cursor={{ fill: '#f1f5f9' }} />
                  <Bar dataKey="percentage" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                    {historyData.map((d, i) => (
                      <Cell key={i} fill={complianceColor(d.percentage)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        )}
      </div>

      {/* Fila 3 — Tablas operativas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel title="OTs por tecnico">
          <Table
            loading={isLoading}
            data={technicians}
            rowKey={(row) => row.technician_id}
            emptyMessage="No hay tecnicos activos con ordenes."
            columns={[
              { key: 'technician_name', header: 'Tecnico' },
              {
                key: 'assigned',
                header: 'Asignadas',
                headerClassName: 'text-right',
                render: (r) => <span className="block text-right tabular-nums">{r.assigned}</span>,
              },
              {
                key: 'completed',
                header: 'Completadas',
                headerClassName: 'text-right',
                render: (r) => <span className="block text-right tabular-nums">{r.completed}</span>,
              },
              {
                key: 'overdue',
                header: 'Vencidas',
                headerClassName: 'text-right',
                render: (r) => (
                  <span
                    className={`block text-right font-semibold tabular-nums ${
                      r.overdue > 0 ? 'text-red-600' : 'text-gray-500'
                    }`}
                  >
                    {r.overdue}
                  </span>
                ),
              },
            ]}
          />
        </Panel>

        <Panel title="Activos sin mantenimiento reciente">
          {isLoading ? (
            <div className="p-5 space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-8 bg-gray-100 rounded animate-pulse" />
              ))}
            </div>
          ) : assetsWithoutPm.length === 0 ? (
            <p className="px-5 py-12 text-center text-sm text-gray-500">
              Todos los activos con plan tienen mantenimiento reciente.
            </p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {assetsWithoutPm.map((a) => (
                <li key={a.asset_id}>
                  <Link
                    to={`/activos/${a.asset_id}`}
                    className="flex items-center justify-between gap-3 px-5 py-3 hover:bg-[#f1f5f9] transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-sm text-gray-800 truncate">{a.asset_name}</p>
                      <p className="text-xs text-gray-500 truncate">{a.hospital_name}</p>
                    </div>
                    <span className="text-sm font-semibold text-red-600 whitespace-nowrap">
                      {a.days_since_last_pm != null ? `${a.days_since_last_pm} dias` : 'Nunca'}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      {/* Fila 4 — Estado de activos */}
      <div>
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Estado de activos</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {ASSET_STATUS_CARDS.map((card) => (
            <Link
              key={card.key}
              to={goToAssets(card.filter)}
              className="block bg-white rounded-xl border border-gray-200 shadow-sm p-4 hover:border-gray-300 hover:shadow transition-all"
            >
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${card.dot}`} />
                <span className="text-xs text-gray-500">{card.label}</span>
              </div>
              {assetsLoading ? (
                <div className="mt-2 h-7 w-12 bg-gray-100 rounded animate-pulse" />
              ) : (
                <p className={`mt-2 text-2xl font-bold ${card.color}`}>
                  {assetsStatus?.[card.key] ?? 0}
                </p>
              )}
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
