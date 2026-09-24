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
import { useContractsSummary } from '../../api/contracts'
import { EstadoDocumento } from '../../components/contracts/ContractStatus'
import KpiCard from '../../components/dashboard/KpiCard'
import Table from '../../components/ui/Table'
import EmptyState from '../../components/ui/EmptyState'
import { CHART, STATUS_COLORS, complianceColor } from '../../constants/palette'

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
  { key: 'on_time', label: 'Al dia', filter: 'on_time', color: 'text-green-700', dot: 'bg-green-600' },
  { key: 'due_soon', label: 'Proximo vencimiento', filter: 'due_soon', color: 'text-amber-700', dot: 'bg-amber-500' },
  { key: 'overdue', label: 'Vencido', filter: 'overdue', color: 'text-red-700', dot: 'bg-red-500' },
  { key: 'no_plan', label: 'Sin protocolo', filter: 'no_plan', color: 'text-gray-700', dot: 'bg-gray-400' },
]

function CardSkeleton() {
  return (
    <div className="card p-5">
      <div className="h-3 w-24 bg-gray-100 rounded-full animate-pulse" />
      <div className="mt-3.5 h-8 w-20 bg-gray-100 rounded-lg animate-pulse" />
      <div className="mt-3 h-3 w-32 bg-gray-100 rounded-full animate-pulse" />
    </div>
  )
}

function ChartSkeleton({ title }) {
  return (
    <div className="card p-5">
      <div className="h-4 w-40 bg-gray-100 rounded-full animate-pulse" />
      <div className="mt-5 h-64 bg-gray-50 rounded-lg animate-pulse" aria-label={title} />
    </div>
  )
}

function Panel({ title, action, children }) {
  return (
    <section className="panel">
      <header className="panel-header">
        <h2 className="text-sm font-semibold text-gray-800">{title}</h2>
        {action}
      </header>
      {children}
    </section>
  )
}

function StatusTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null
  const item = payload[0]
  return (
    <div className="bg-white ring-1 ring-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-medium text-gray-800">{item.name}</p>
      <p className="mt-0.5 font-mono text-gray-500">{item.value} orden(es)</p>
    </div>
  )
}

function ComplianceTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null
  const d = payload[0].payload
  if (d.percentage == null) {
    return (
      <div className="bg-white ring-1 ring-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
        <p className="font-medium text-gray-800">{d.label}</p>
        <p className="mt-0.5 text-gray-500">Sin datos</p>
      </div>
    )
  }
  return (
    <div className="bg-white ring-1 ring-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-medium text-gray-800">
        {d.label}: <span className="font-mono">{d.percentage}%</span>
      </p>
      <p className="mt-0.5 font-mono text-gray-500">
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
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
        <div>
          <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Indicadores de gestion de mantenimiento
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label htmlFor="filtro-hospital" className="block label-meta mb-1.5">
              Hospital
            </label>
            <select
              id="filtro-hospital"
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
            <p className="label-meta mb-1.5">Periodo</p>
            {/* Segmentos sobre un rail hundido: el activo sube como una ficha
                en vez de pintar de azul un tercio de la barra. */}
            <div
              role="group"
              aria-label="Periodo del informe"
              className="inline-flex gap-1 p-1 rounded-lg bg-gray-100 ring-1 ring-inset ring-gray-200"
            >
              {PERIODS.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  onClick={() => setDays(p.value)}
                  aria-pressed={days === p.value}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium
                    transition-[background-color,color,box-shadow] duration-150
                    focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/25 ${
                      days === p.value
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-500 hover:text-gray-800'
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
        <div
          role="alert"
          className="flex items-start justify-between gap-4 px-4 py-3 rounded-lg bg-red-50 ring-1 ring-inset ring-red-200 text-red-800 text-sm"
        >
          <span>No se pudieron cargar los indicadores.</span>
          <button type="button" onClick={handleRefresh} className="btn-link text-red-700">
            Reintentar
          </button>
        </div>
      )}

      {/* Fila 1 — KPIs principales */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger">
        {isLoading ? (
          [...Array(4)].map((_, i) => <CardSkeleton key={i} />)
        ) : (
          <>
            <KpiCard
              title="Cumplimiento de protocolos"
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
                <EmptyState
                  compact
                  icon="workOrder"
                  title="Sin ordenes en el periodo"
                  description="Amplia el rango de fechas o quita el filtro de hospital para ver actividad."
                />
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
                      stroke={CHART.surface}
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
                    tick={{ fontSize: 12, fill: CHART.axis }}
                    axisLine={{ stroke: CHART.grid }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, 100]}
                    ticks={[0, 25, 50, 75, 100]}
                    tick={{ fontSize: 12, fill: CHART.axis }}
                    axisLine={false}
                    tickLine={false}
                    unit="%"
                  />
                  <Tooltip content={<ComplianceTooltip />} cursor={{ fill: CHART.cursor }} />
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
            <EmptyState
              compact
              icon="checkCircle"
              title="Todo al dia"
              description="Ningún activo con protocolo asignado lleva demasiado tiempo sin intervencion."
            />
          ) : (
            <ul className="divide-y divide-gray-100">
              {assetsWithoutPm.map((a) => (
                <li key={a.asset_id}>
                  <Link
                    to={`/activos/${a.asset_id}`}
                    className="flex items-center justify-between gap-3 px-5 py-3 hover:bg-brand-50/60 transition-colors"
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

      <ContratosPorVencer hospitalId={hospitalId} />

      {/* Fila 4 — Estado de activos */}
      <div>
        <h2 className="text-sm font-semibold text-gray-800 mb-3">Estado de activos</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {ASSET_STATUS_CARDS.map((card) => (
            <Link
              key={card.key}
              to={goToAssets(card.filter)}
              className="card-interactive block p-4"
            >
              <div className="flex items-center gap-2">
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${card.dot}`} aria-hidden="true" />
                <span className="label-meta truncate">{card.label}</span>
              </div>
              {assetsLoading ? (
                <div className="mt-2.5 h-7 w-12 bg-gray-100 rounded-lg animate-pulse" />
              ) : (
                <p className={`mt-2.5 text-[1.625rem] leading-none stat-value ${card.color}`}>
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

/**
 * Contratos y garantías que vencen en 60 días y hospitales sin contrato
 * vigente. Solo aparece si hay algo que atender.
 */
function ContratosPorVencer({ hospitalId }) {
  const { data } = useContractsSummary()
  const deEste = (id) => !hospitalId || id === hospitalId
  const porVencer = (data?.expiring ?? []).filter((c) => deEste(c.hospital_id))
  const sinContrato = (data?.hospitals_without_contract ?? []).filter((h) => deEste(h.id))
  if (!porVencer.length && !sinContrato.length) return null
  return (
    <Panel title="Contratos y garantías"
      action={<Link to="/contratos" className="btn-link text-sm">Ver todos</Link>}>
      <ul className="divide-y divide-gray-100">
        {sinContrato.map((h) => (
          <li key={h.id} className="flex items-center justify-between gap-3 px-5 py-3">
            <p className="text-sm text-gray-800 truncate">{h.name}</p>
            <span className="text-xs px-2 py-0.5 rounded-full bg-red-50 text-red-700 font-medium whitespace-nowrap">Sin contrato vigente</span>
          </li>
        ))}
        {porVencer.map((c) => (
          <li key={c.id} className="flex items-center justify-between gap-3 px-5 py-3">
            <div className="min-w-0">
              <p className="text-sm text-gray-800 truncate">{c.name}</p>
              <p className="text-xs text-gray-500 truncate">{c.hospital_name}</p>
            </div>
            <EstadoDocumento doc={c} />
          </li>
        ))}
      </ul>
    </Panel>
  )
}
