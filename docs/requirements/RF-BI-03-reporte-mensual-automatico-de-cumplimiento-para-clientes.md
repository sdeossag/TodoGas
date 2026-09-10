---
id: RF-BI-03
issue: 41
titulo: "Reporte mensual automático de cumplimiento para clientes"
tipo: functional
prioridad: should-have
modulo: dashboard-bi
estado: OPEN
etiquetas: ['priority: should-have', 'type: functional', 'mod: dashboard-bi']
---

# RF-BI-03 - Reporte mensual automático de cumplimiento para clientes

### RF-BI-03: Reporte mensual automático de cumplimiento para clientes
**Prioridad:** S

**Descripción:**
El sistema genera y envía automáticamente un reporte mensual de cumplimiento del plan de mantenimiento a cada hospital al inicio de cada mes.

**Criterios de aceptación:**
- El reporte se genera automáticamente el **primer día de cada mes a las 08:00 AM** (hora Colombia, UTC-5) con datos del mes anterior completo.
- **Contenido del reporte mensual:**
  - Listado de activos del hospital con su plan de mantenimiento vigente.
  - Por cada activo: OTs ejecutadas en el mes (tipo, fecha, técnico, estado), OTs vencidas si las hay, próxima fecha programada de mantenimiento.
  - Porcentaje de cumplimiento del plan del hospital para el mes.
  - Gráfico de OTs por tipo del mes.
- Se envía al correo principal del hospital con CC al `ADMIN`.
- El `ADMIN` puede pausar el envío automático para un hospital específico desde la configuración del hospital.
- El `ADMIN` puede generar y enviar manualmente el reporte mensual de cualquier hospital para cualquier período pasado.

---

## MÓDULO IN — Inventario de Repuestos
