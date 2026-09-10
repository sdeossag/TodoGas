---
id: RF-PM-03
issue: 18
titulo: "Vista de cumplimiento de planes"
tipo: functional
prioridad: must-have
modulo: planes-pm
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: planes-pm']
---

# RF-PM-03 - Vista de cumplimiento de planes

### RF-PM-03: Vista de cumplimiento de planes
**Prioridad:** M

**Descripción:**
El sistema ofrece una vista específica del estado de cumplimiento de cada plan activo, para que el `ADMIN` y `SUP` identifiquen fácilmente los planes con rezago.

**Criterios de aceptación:**
- Por cada plan activo se muestra en la vista de cumplimiento: nombre del plan, alcance (activos que cubre), técnico asignado por defecto, próxima fecha de ejecución, última ejecución completada (con enlace a esa OT), % de cumplimiento del mes actual (OTs completadas a tiempo / OTs generadas en el mes).
- Indicador visual de salud del plan:
  - 🟢 **Al día:** todas las OTs del mes completadas en término.
  - 🟡 **Con retraso:** al menos 1 OT del mes no completada en la fecha límite pero completada después.
  - 🔴 **Crítico:** al menos 1 OT del mes sin completar (vencida) o 2 ejecuciones consecutivas sin completar en el historial.
- El ADMIN puede ver el histórico de cumplimiento mes a mes por plan (tabla con el % por mes de los últimos 12 meses).
- Esta información alimenta el KPI de "Cumplimiento de Planes Preventivos" del dashboard de BI.
