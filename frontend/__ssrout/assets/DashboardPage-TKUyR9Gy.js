import { jsxs, jsx, Fragment } from "react/jsx-runtime";
import { useState, useMemo } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, BarChart, XAxis, YAxis, Bar } from "recharts";
import client from "./client-xYrMAKmr.js";
import "axios";
const DASHBOARD_STALE_TIME = 5 * 60 * 1e3;
function useDashboard(params = {}) {
  return useQuery({
    queryKey: ["dashboard", params],
    queryFn: () => client.get("/api/dashboard/", { params }).then((r) => r.data),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: false
  });
}
function useComplianceHistory(params = {}) {
  return useQuery({
    queryKey: ["dashboard", "compliance-history", params],
    queryFn: () => client.get("/api/dashboard/compliance-history/", { params }).then((r) => r.data),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: false
  });
}
function useAssetsStatus(params = {}) {
  return useQuery({
    queryKey: ["dashboard", "assets-status", params],
    queryFn: () => client.get("/api/dashboard/assets-status/", { params }).then((r) => r.data),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: false
  });
}
function useHospitals(params = {}) {
  return useQuery({
    queryKey: ["hospitals", params],
    queryFn: () => client.get("/api/hospitals/", { params }).then((r) => r.data)
  });
}
const COLOR_STYLES = {
  green: { value: "text-green-600", accent: "bg-green-500" },
  yellow: { value: "text-amber-600", accent: "bg-amber-500" },
  red: { value: "text-red-600", accent: "bg-red-500" },
  blue: { value: "text-blue-600", accent: "bg-blue-500" },
  gray: { value: "text-gray-700", accent: "bg-gray-400" }
};
function KpiCard({
  title,
  value,
  subtitle,
  trend,
  trendDirection,
  color = "gray"
}) {
  const styles = COLOR_STYLES[color] ?? COLOR_STYLES.gray;
  const trendUp = trendDirection === "up";
  return /* @__PURE__ */ jsxs("div", { className: "relative bg-white rounded-xl border border-gray-200 shadow-sm p-5 overflow-hidden", children: [
    /* @__PURE__ */ jsx("span", { className: `absolute inset-y-0 left-0 w-1 ${styles.accent}`, "aria-hidden": "true" }),
    /* @__PURE__ */ jsx("p", { className: "text-xs font-medium text-gray-400 uppercase tracking-wider", children: title }),
    /* @__PURE__ */ jsx("p", { className: `mt-2 text-3xl font-bold leading-none ${styles.value}`, children: value }),
    subtitle && /* @__PURE__ */ jsx("p", { className: "mt-2 text-sm text-gray-500", children: subtitle }),
    trend != null && trend !== "" && /* @__PURE__ */ jsxs(
      "div",
      {
        className: `mt-3 inline-flex items-center gap-1 text-xs font-semibold ${trendUp ? "text-green-600" : "text-red-600"}`,
        children: [
          /* @__PURE__ */ jsx("svg", { className: "w-3.5 h-3.5", viewBox: "0 0 12 12", fill: "currentColor", "aria-hidden": "true", children: trendUp ? /* @__PURE__ */ jsx("path", { d: "M6 2l4 6H2z" }) : /* @__PURE__ */ jsx("path", { d: "M6 10L2 4h8z" }) }),
          /* @__PURE__ */ jsx("span", { children: trend })
        ]
      }
    )
  ] });
}
function complianceColor(percentage) {
  if (percentage == null) return "#9ca3af";
  if (percentage >= 80) return "#16a34a";
  if (percentage >= 50) return "#ca8a04";
  return "#dc2626";
}
function Table({
  columns = [],
  data = [],
  loading = false,
  emptyMessage = "Sin registros.",
  rowKey = (row, i) => row.id ?? i,
  onRowClick
}) {
  return /* @__PURE__ */ jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxs("table", { className: "w-full text-sm", children: [
    /* @__PURE__ */ jsx("thead", { children: /* @__PURE__ */ jsx("tr", { className: "bg-[#f8fafc] border-b border-gray-200", children: columns.map((col) => /* @__PURE__ */ jsx(
      "th",
      {
        className: `px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap ${col.headerClassName ?? ""}`,
        children: col.header
      },
      col.key
    )) }) }),
    /* @__PURE__ */ jsx("tbody", { className: "divide-y divide-gray-100", children: loading ? [...Array(4)].map((_, i) => /* @__PURE__ */ jsx("tr", { children: columns.map((col) => /* @__PURE__ */ jsx("td", { className: "px-4 py-3", children: /* @__PURE__ */ jsx("div", { className: "h-3 bg-gray-100 rounded animate-pulse" }) }, col.key)) }, `skeleton-${i}`)) : data.length === 0 ? /* @__PURE__ */ jsx("tr", { children: /* @__PURE__ */ jsx(
      "td",
      {
        colSpan: columns.length || 1,
        className: "px-4 py-12 text-center text-sm text-gray-400",
        children: emptyMessage
      }
    ) }) : data.map((row, i) => /* @__PURE__ */ jsx(
      "tr",
      {
        onClick: onRowClick ? () => onRowClick(row) : void 0,
        className: `hover:bg-[#f1f5f9] transition-colors ${onRowClick ? "cursor-pointer" : ""}`,
        children: columns.map((col) => /* @__PURE__ */ jsx(
          "td",
          {
            className: `px-4 py-3 text-gray-700 ${col.className ?? ""}`,
            children: col.render ? col.render(row) : row[col.key] ?? "—"
          },
          col.key
        ))
      },
      rowKey(row, i)
    )) })
  ] }) });
}
const STATUS_COLORS = {
  PENDING: "#9ca3af",
  IN_PROGRESS: "#3b82f6",
  IN_REVIEW: "#f59e0b",
  COMPLETED: "#16a34a",
  CANCELLED: "#ef4444"
};
const STATUS_LABELS = {
  PENDING: "Pendiente",
  IN_PROGRESS: "En proceso",
  IN_REVIEW: "En revision",
  COMPLETED: "Finalizada",
  CANCELLED: "Cancelada"
};
const MONTH_ABBR = [
  "Ene",
  "Feb",
  "Mar",
  "Abr",
  "May",
  "Jun",
  "Jul",
  "Ago",
  "Sep",
  "Oct",
  "Nov",
  "Dic"
];
const PERIODS = [
  { value: 7, label: "7 dias" },
  { value: 30, label: "30 dias" },
  { value: 90, label: "90 dias" }
];
const ASSET_STATUS_CARDS = [
  { key: "on_time", label: "Al dia", filter: "on_time", color: "text-green-600", dot: "bg-green-500" },
  { key: "due_soon", label: "Proximo vencimiento", filter: "due_soon", color: "text-amber-600", dot: "bg-amber-500" },
  { key: "overdue", label: "Vencido", filter: "overdue", color: "text-red-600", dot: "bg-red-500" },
  { key: "no_plan", label: "Sin plan", filter: "no_plan", color: "text-gray-600", dot: "bg-gray-400" }
];
function CardSkeleton() {
  return /* @__PURE__ */ jsxs("div", { className: "bg-white rounded-xl border border-gray-200 shadow-sm p-5", children: [
    /* @__PURE__ */ jsx("div", { className: "h-3 w-24 bg-gray-100 rounded animate-pulse" }),
    /* @__PURE__ */ jsx("div", { className: "mt-3 h-8 w-20 bg-gray-100 rounded animate-pulse" }),
    /* @__PURE__ */ jsx("div", { className: "mt-3 h-3 w-32 bg-gray-100 rounded animate-pulse" })
  ] });
}
function ChartSkeleton({ title }) {
  return /* @__PURE__ */ jsxs("div", { className: "bg-white rounded-xl border border-gray-200 shadow-sm p-5", children: [
    /* @__PURE__ */ jsx("div", { className: "h-4 w-40 bg-gray-100 rounded animate-pulse" }),
    /* @__PURE__ */ jsx("div", { className: "mt-5 h-64 bg-gray-50 rounded-lg animate-pulse", "aria-label": title })
  ] });
}
function Panel({ title, children }) {
  return /* @__PURE__ */ jsxs("div", { className: "bg-white rounded-xl border border-gray-200 shadow-sm", children: [
    /* @__PURE__ */ jsx("div", { className: "flex items-center justify-between px-5 py-4 border-b border-gray-100", children: /* @__PURE__ */ jsx("h2", { className: "text-sm font-semibold text-gray-700", children: title }) }),
    children
  ] });
}
function StatusTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0];
  return /* @__PURE__ */ jsxs("div", { className: "bg-white border border-gray-200 rounded-lg shadow-md px-3 py-2 text-xs", children: [
    /* @__PURE__ */ jsx("p", { className: "font-medium text-gray-700", children: item.name }),
    /* @__PURE__ */ jsxs("p", { className: "text-gray-500", children: [
      item.value,
      " orden(es)"
    ] })
  ] });
}
function ComplianceTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  if (d.percentage == null) {
    return /* @__PURE__ */ jsxs("div", { className: "bg-white border border-gray-200 rounded-lg shadow-md px-3 py-2 text-xs", children: [
      /* @__PURE__ */ jsx("p", { className: "font-medium text-gray-700", children: d.label }),
      /* @__PURE__ */ jsx("p", { className: "text-gray-400", children: "Sin datos" })
    ] });
  }
  return /* @__PURE__ */ jsxs("div", { className: "bg-white border border-gray-200 rounded-lg shadow-md px-3 py-2 text-xs", children: [
    /* @__PURE__ */ jsxs("p", { className: "font-medium text-gray-700", children: [
      d.label,
      ": ",
      d.percentage,
      "%"
    ] }),
    /* @__PURE__ */ jsxs("p", { className: "text-gray-500", children: [
      d.completed,
      " completadas / ",
      d.generated,
      " generadas"
    ] })
  ] });
}
function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [hospitalId, setHospitalId] = useState("");
  const [days, setDays] = useState(30);
  const params = useMemo(() => {
    const p = { days };
    if (hospitalId) p.hospital_id = hospitalId;
    return p;
  }, [hospitalId, days]);
  const historyParams = useMemo(
    () => hospitalId ? { hospital_id: hospitalId, months: 12 } : { months: 12 },
    [hospitalId]
  );
  const assetsParams = useMemo(
    () => hospitalId ? { hospital_id: hospitalId } : {},
    [hospitalId]
  );
  const { data: hospitals = [] } = useHospitals();
  const { data, isLoading, isFetching, error } = useDashboard(params);
  const { data: history = [], isLoading: historyLoading } = useComplianceHistory(historyParams);
  const { data: assetsStatus, isLoading: assetsLoading } = useAssetsStatus(assetsParams);
  const hospitalList = Array.isArray(hospitals) ? hospitals : (hospitals == null ? void 0 : hospitals.results) ?? [];
  function goToAssets(maintenanceStatus) {
    const qs = new URLSearchParams({ maintenance_status: maintenanceStatus });
    if (hospitalId) qs.set("hospital_id", hospitalId);
    return `/activos?${qs.toString()}`;
  }
  function handleRefresh() {
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  }
  const compliance = data == null ? void 0 : data.compliance;
  const mttr = data == null ? void 0 : data.mttr;
  const overdue = data == null ? void 0 : data.overdue;
  const otsByStatus = (data == null ? void 0 : data.ots_by_status) ?? {};
  const totalOts = Object.values(otsByStatus).reduce((a, b) => a + b, 0);
  const pieData = Object.entries(STATUS_COLORS).map(([status, color]) => ({
    status,
    name: STATUS_LABELS[status],
    value: otsByStatus[status] ?? 0,
    color
  })).filter((d) => d.value > 0);
  const historyData = (history ?? []).map((h) => {
    const [year, month] = (h.month ?? "").split("-");
    const idx = parseInt(month, 10) - 1;
    const abbr = MONTH_ABBR[idx] ?? h.month;
    return {
      label: year ? `${abbr} ${year}` : abbr,
      month: abbr,
      percentage: h.generated > 0 ? h.percentage : null,
      completed: h.completed,
      generated: h.generated
    };
  });
  const technicians = [...(data == null ? void 0 : data.ots_by_technician) ?? []].sort((a, b) => b.overdue - a.overdue);
  const assetsWithoutPm = ((data == null ? void 0 : data.assets_without_maintenance) ?? []).slice(0, 10);
  const complianceColorName = compliance == null ? "gray" : compliance.percentage >= 80 ? "green" : compliance.percentage >= 50 ? "yellow" : "red";
  return /* @__PURE__ */ jsxs("div", { className: "space-y-6", children: [
    /* @__PURE__ */ jsxs("div", { className: "flex flex-wrap items-end justify-between gap-4", children: [
      /* @__PURE__ */ jsxs("div", { children: [
        /* @__PURE__ */ jsx("h1", { className: "text-2xl font-bold text-gray-800", children: "Dashboard" }),
        /* @__PURE__ */ jsx("p", { className: "text-sm text-gray-400 mt-0.5", children: "Indicadores de gestion de mantenimiento" })
      ] }),
      /* @__PURE__ */ jsxs("div", { className: "flex flex-wrap items-end gap-3", children: [
        /* @__PURE__ */ jsxs("div", { children: [
          /* @__PURE__ */ jsx("label", { className: "block text-xs text-gray-500 mb-1", children: "Hospital" }),
          /* @__PURE__ */ jsxs(
            "select",
            {
              value: hospitalId,
              onChange: (e) => setHospitalId(e.target.value),
              className: "input-field w-56 py-2",
              children: [
                /* @__PURE__ */ jsx("option", { value: "", children: "Todos los hospitales" }),
                hospitalList.map((h) => /* @__PURE__ */ jsx("option", { value: h.id, children: h.name }, h.id))
              ]
            }
          )
        ] }),
        /* @__PURE__ */ jsxs("div", { children: [
          /* @__PURE__ */ jsx("label", { className: "block text-xs text-gray-500 mb-1", children: "Periodo" }),
          /* @__PURE__ */ jsx("div", { className: "inline-flex rounded-md border border-gray-300 overflow-hidden", children: PERIODS.map((p) => /* @__PURE__ */ jsx(
            "button",
            {
              type: "button",
              onClick: () => setDays(p.value),
              className: `px-3 py-2 text-sm font-medium transition-colors ${days === p.value ? "bg-primary-800 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`,
              children: p.label
            },
            p.value
          )) })
        ] }),
        /* @__PURE__ */ jsx(
          "button",
          {
            type: "button",
            onClick: handleRefresh,
            className: "btn-secondary",
            disabled: isFetching,
            children: isFetching ? "Actualizando..." : "Actualizar"
          }
        )
      ] })
    ] }),
    error && /* @__PURE__ */ jsx("div", { className: "px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm", children: "No se pudieron cargar los indicadores. Intenta de nuevo." }),
    /* @__PURE__ */ jsx("div", { className: "grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4", children: isLoading ? [...Array(4)].map((_, i) => /* @__PURE__ */ jsx(CardSkeleton, {}, i)) : /* @__PURE__ */ jsxs(Fragment, { children: [
      /* @__PURE__ */ jsx(
        KpiCard,
        {
          title: "Cumplimiento de planes",
          value: `${(compliance == null ? void 0 : compliance.percentage) ?? 0}%`,
          subtitle: `${(compliance == null ? void 0 : compliance.completed) ?? 0}/${(compliance == null ? void 0 : compliance.generated) ?? 0} OTs`,
          color: complianceColorName
        }
      ),
      /* @__PURE__ */ jsx(
        KpiCard,
        {
          title: "MTTR (tiempo medio de reparacion)",
          value: `${((mttr == null ? void 0 : mttr.mttr_hours) ?? 0).toFixed(1)}h`,
          subtitle: `Basado en ${(mttr == null ? void 0 : mttr.sample_size) ?? 0} OTs correctivas`,
          color: "blue"
        }
      ),
      /* @__PURE__ */ jsx(
        KpiCard,
        {
          title: "OTs vencidas",
          value: (overdue == null ? void 0 : overdue.count) ?? 0,
          subtitle: `${(overdue == null ? void 0 : overdue.critical) ?? 0} criticas (prioridad alta)`,
          color: ((overdue == null ? void 0 : overdue.count) ?? 0) > 0 ? "red" : "green"
        }
      ),
      /* @__PURE__ */ jsx(
        KpiCard,
        {
          title: "OTs completadas este periodo",
          value: otsByStatus.COMPLETED ?? 0,
          subtitle: `De ${totalOts} ordenes en el periodo`,
          color: "blue"
        }
      )
    ] }) }),
    /* @__PURE__ */ jsxs("div", { className: "grid grid-cols-1 lg:grid-cols-2 gap-4", children: [
      isLoading ? /* @__PURE__ */ jsx(ChartSkeleton, { title: "OTs por estado" }) : /* @__PURE__ */ jsx(Panel, { title: "OTs por estado", children: /* @__PURE__ */ jsxs("div", { className: "p-5", children: [
        pieData.length === 0 ? /* @__PURE__ */ jsx("div", { className: "h-[260px] flex items-center justify-center text-sm text-gray-400", children: "Sin ordenes en el periodo seleccionado." }) : /* @__PURE__ */ jsx(ResponsiveContainer, { width: "100%", height: 260, children: /* @__PURE__ */ jsxs(PieChart, { children: [
          /* @__PURE__ */ jsx(
            Pie,
            {
              data: pieData,
              dataKey: "value",
              nameKey: "name",
              innerRadius: 65,
              outerRadius: 100,
              paddingAngle: 2,
              stroke: "#ffffff",
              strokeWidth: 2,
              isAnimationActive: false,
              children: pieData.map((entry) => /* @__PURE__ */ jsx(Cell, { fill: entry.color }, entry.status))
            }
          ),
          /* @__PURE__ */ jsx(Tooltip, { content: /* @__PURE__ */ jsx(StatusTooltip, {}) })
        ] }) }),
        /* @__PURE__ */ jsx("ul", { className: "mt-4 grid grid-cols-2 gap-x-6 gap-y-2", children: Object.entries(STATUS_COLORS).map(([status, color]) => /* @__PURE__ */ jsxs("li", { className: "flex items-center gap-2 text-sm", children: [
          /* @__PURE__ */ jsx(
            "span",
            {
              className: "w-2.5 h-2.5 rounded-full flex-shrink-0",
              style: { backgroundColor: color }
            }
          ),
          /* @__PURE__ */ jsx("span", { className: "text-gray-600 flex-1", children: STATUS_LABELS[status] }),
          /* @__PURE__ */ jsx("span", { className: "font-semibold text-gray-800 tabular-nums", children: otsByStatus[status] ?? 0 })
        ] }, status)) })
      ] }) }),
      historyLoading ? /* @__PURE__ */ jsx(ChartSkeleton, { title: "Cumplimiento ultimos 12 meses" }) : /* @__PURE__ */ jsx(Panel, { title: "Cumplimiento — ultimos 12 meses", children: /* @__PURE__ */ jsx("div", { className: "p-5", children: /* @__PURE__ */ jsx(ResponsiveContainer, { width: "100%", height: 260, children: /* @__PURE__ */ jsxs(BarChart, { data: historyData, margin: { top: 8, right: 8, left: -18, bottom: 0 }, children: [
        /* @__PURE__ */ jsx(
          XAxis,
          {
            dataKey: "month",
            tick: { fontSize: 12, fill: "#6b7280" },
            axisLine: { stroke: "#e5e7eb" },
            tickLine: false
          }
        ),
        /* @__PURE__ */ jsx(
          YAxis,
          {
            domain: [0, 100],
            ticks: [0, 25, 50, 75, 100],
            tick: { fontSize: 12, fill: "#6b7280" },
            axisLine: false,
            tickLine: false,
            unit: "%"
          }
        ),
        /* @__PURE__ */ jsx(Tooltip, { content: /* @__PURE__ */ jsx(ComplianceTooltip, {}), cursor: { fill: "#f1f5f9" } }),
        /* @__PURE__ */ jsx(Bar, { dataKey: "percentage", radius: [4, 4, 0, 0], isAnimationActive: false, children: historyData.map((d, i) => /* @__PURE__ */ jsx(Cell, { fill: complianceColor(d.percentage) }, i)) })
      ] }) }) }) })
    ] }),
    /* @__PURE__ */ jsxs("div", { className: "grid grid-cols-1 lg:grid-cols-2 gap-4", children: [
      /* @__PURE__ */ jsx(Panel, { title: "OTs por tecnico", children: /* @__PURE__ */ jsx(
        Table,
        {
          loading: isLoading,
          data: technicians,
          rowKey: (row) => row.technician_id,
          emptyMessage: "No hay tecnicos activos con ordenes.",
          columns: [
            { key: "technician_name", header: "Tecnico" },
            {
              key: "assigned",
              header: "Asignadas",
              headerClassName: "text-right",
              render: (r) => /* @__PURE__ */ jsx("span", { className: "block text-right tabular-nums", children: r.assigned })
            },
            {
              key: "completed",
              header: "Completadas",
              headerClassName: "text-right",
              render: (r) => /* @__PURE__ */ jsx("span", { className: "block text-right tabular-nums", children: r.completed })
            },
            {
              key: "overdue",
              header: "Vencidas",
              headerClassName: "text-right",
              render: (r) => /* @__PURE__ */ jsx(
                "span",
                {
                  className: `block text-right font-semibold tabular-nums ${r.overdue > 0 ? "text-red-600" : "text-gray-500"}`,
                  children: r.overdue
                }
              )
            }
          ]
        }
      ) }),
      /* @__PURE__ */ jsx(Panel, { title: "Activos sin mantenimiento reciente", children: isLoading ? /* @__PURE__ */ jsx("div", { className: "p-5 space-y-3", children: [...Array(5)].map((_, i) => /* @__PURE__ */ jsx("div", { className: "h-8 bg-gray-100 rounded animate-pulse" }, i)) }) : assetsWithoutPm.length === 0 ? /* @__PURE__ */ jsx("p", { className: "px-5 py-12 text-center text-sm text-gray-400", children: "Todos los activos con plan tienen mantenimiento reciente." }) : /* @__PURE__ */ jsx("ul", { className: "divide-y divide-gray-100", children: assetsWithoutPm.map((a) => /* @__PURE__ */ jsx("li", { children: /* @__PURE__ */ jsxs(
        Link,
        {
          to: `/activos/${a.asset_id}`,
          className: "flex items-center justify-between gap-3 px-5 py-3 hover:bg-[#f1f5f9] transition-colors",
          children: [
            /* @__PURE__ */ jsxs("div", { className: "min-w-0", children: [
              /* @__PURE__ */ jsx("p", { className: "text-sm text-gray-800 truncate", children: a.asset_name }),
              /* @__PURE__ */ jsx("p", { className: "text-xs text-gray-400 truncate", children: a.hospital_name })
            ] }),
            /* @__PURE__ */ jsx("span", { className: "text-sm font-semibold text-red-600 whitespace-nowrap", children: a.days_since_last_pm != null ? `${a.days_since_last_pm} dias` : "Nunca" })
          ]
        }
      ) }, a.asset_id)) }) })
    ] }),
    /* @__PURE__ */ jsxs("div", { children: [
      /* @__PURE__ */ jsx("h2", { className: "text-sm font-semibold text-gray-700 mb-3", children: "Estado de activos" }),
      /* @__PURE__ */ jsx("div", { className: "grid grid-cols-2 lg:grid-cols-4 gap-4", children: ASSET_STATUS_CARDS.map((card) => /* @__PURE__ */ jsxs(
        "button",
        {
          type: "button",
          onClick: () => navigate(goToAssets(card.filter)),
          className: "text-left bg-white rounded-xl border border-gray-200 shadow-sm p-4 hover:border-gray-300 hover:shadow transition-all",
          children: [
            /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-2", children: [
              /* @__PURE__ */ jsx("span", { className: `w-2 h-2 rounded-full ${card.dot}` }),
              /* @__PURE__ */ jsx("span", { className: "text-xs text-gray-500", children: card.label })
            ] }),
            assetsLoading ? /* @__PURE__ */ jsx("div", { className: "mt-2 h-7 w-12 bg-gray-100 rounded animate-pulse" }) : /* @__PURE__ */ jsx("p", { className: `mt-2 text-2xl font-bold ${card.color}`, children: (assetsStatus == null ? void 0 : assetsStatus[card.key]) ?? 0 })
          ]
        },
        card.key
      )) })
    ] })
  ] });
}
export {
  DashboardPage as default
};
