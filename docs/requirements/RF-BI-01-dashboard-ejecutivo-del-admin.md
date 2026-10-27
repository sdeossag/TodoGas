---
id: RF-BI-01
issue: 39
titulo: "Dashboard ejecutivo del ADMIN"
tipo: functional
prioridad: must-have
modulo: dashboard-bi
estado: OPEN
etiquetas: ['priority: must-have', 'type: functional', 'mod: dashboard-bi']
---

# RF-BI-01 - Dashboard ejecutivo del ADMIN

### RF-BI-01: Dashboard ejecutivo del ADMIN
**Prioridad:** M

**Descripción:**
El `ADMIN` tiene un dashboard con los KPIs operativos clave, actualizado con datos frescos (retraso máximo 5 minutos), con gráficos interactivos y filtros.

**Criterios de aceptación:**
- **KPIs del dashboard:**
  - **Cumplimiento de planes preventivos:** % de OTs preventivas completadas en término / total OTs preventivas generadas en el mes actual. Comparativa con mes anterior (flecha de tendencia).
  - **OTs vencidas:** conteo de OTs cuya fecha límite ya pasó y están en estado Pendiente o En Progreso. Con drill-down al listado.
  - **OTs por estado (mes actual):** gráfico de donut o barras con conteo de OTs en cada estado.
  - **MTTR (correctivas):** tiempo promedio (horas) entre el inicio real y el cierre de OTs correctivas, del mes actual vs. mes anterior.
  - **Activos sin mantenimiento reciente:** listado de activos que superan X días sin ninguna OT completada. X es configurable por el ADMIN (por defecto 90 días).
  - **OTs por técnico (mes):** tabla con OTs asignadas, completadas, y vencidas por cada técnico.
- Cada KPI tiene: valor actual, comparativa con período anterior (flecha + porcentaje de cambio), y al hacer clic en el valor numérico, filtra el listado de OTs correspondiente.
- El dashboard tiene filtros globales de: hospital (multi-selección), tipo de OT, rango de fechas. Al aplicar un filtro, todos los KPIs se recalculan.
- Los gráficos son interactivos: click en un segmento filtra el listado debajo del dashboard.

---

---

**Metadatos de importacion**
- Repositorio destino: `sdeossag/TodoGas`
- Modulo: `BI - Dashboard y Reportes de Gestión`
- Prioridad: `M`
- Fuente: `CMMS_Fase1_Requisitos_Funcionales.md`

**Implementación (revisión del 2026-10-27):**
- [x] KPI cumplimiento preventivo del mes — calculate_compliance_percentage más historial de 12 meses.
- [ ] Comparativa con mes anterior y flecha de tendencia — Solo hay gráfico de barras mensual, sin flecha ni % de cambio en los KPI.
- [x] OT vencidas — calculate_overdue_count.
- [x] OT por estado en gráfico — Gráfico circular en DashboardPage.
- [x] MTTR de correctivas — Sin comparar con el mes anterior.
- [ ] Activos sin mantenimiento reciente, X configurable — Lista con 90 días fijos; el ADMIN no puede cambiar X.
- [x] OT por técnico: asignadas, completadas, vencidas — calculate_ots_by_technician.
- [x] Datos con retraso máximo de 5 minutos — Caché de 300 s.
- [ ] Filtros globales: hospital multi, tipo de OT, rango de fechas — Hay un solo hospital y periodos de 30/90 días; sin tipo de OT ni fechas libres.
- [ ] Clic en KPI o gráfico filtra el listado de OT — Los enlaces llevan a activos, no a un listado de OT filtrado.

Commits: 16c6079, 5ed8863, 308967d
Archivos: `backend/apps/work_orders/dashboard.py`, `backend/apps/work_orders/views_dashboard.py`, `frontend/src/pages/dashboard/DashboardPage.jsx`
