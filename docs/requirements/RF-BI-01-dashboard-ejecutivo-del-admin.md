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
