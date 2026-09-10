---
id: RF-BI-02
issue: 40
titulo: "KPIs avanzados: MTBF y costos"
tipo: functional
prioridad: should-have
modulo: dashboard-bi
estado: OPEN
etiquetas: ['priority: should-have', 'type: functional', 'mod: dashboard-bi']
---

# RF-BI-02 - KPIs avanzados: MTBF y costos

### RF-BI-02: KPIs avanzados: MTBF y costos
**Prioridad:** S

**Descripción:**
El sistema calcula el MTBF por activo y permite el registro de costos por OT para reportes financieros de mantenimiento.

**Criterios de aceptación:**
- **MTBF por activo:** tiempo promedio (días) entre dos OTs correctivas consecutivas del mismo activo. Se calcula sobre las últimas 12 meses. Requiere mínimo 2 OTs correctivas del mismo activo para mostrarse (si no, muestra "Datos insuficientes").
- El `ADMIN` puede registrar el costo de una OT al completarla: mano de obra (horas trabajadas × tarifa por hora configurable por técnico), materiales (suma automática de repuestos de inventario usados con su precio unitario), y otros costos (campo libre con valor en COP).
- El registro de costos es opcional; las OTs sin costo registrado se muestran como "Costo no registrado" en los reportes.
- El dashboard muestra: costo total de mantenimiento del mes, desglosado por tipo de OT y por hospital.
- El costo promedio por OT correctiva vs. preventiva es un KPI adicional en el dashboard.
