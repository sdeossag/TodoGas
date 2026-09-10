---
id: RF-OT-01
issue: 8
titulo: "Tipos de órdenes de trabajo"
tipo: functional
prioridad: must-have
modulo: ordenes-trabajo
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: ordenes-trabajo']
---

# RF-OT-01 - Tipos de órdenes de trabajo

### RF-OT-01: Tipos de órdenes de trabajo
**Prioridad:** M

**Descripción:**
El sistema distingue 3 tipos de OT con comportamientos y flujos diferenciados: **Correctiva** (generada manualmente por el ADMIN ante una falla), **Preventiva** (generada automáticamente por el sistema según un plan de mantenimiento), y **Predictiva** (generada manualmente por el ADMIN basada en lecturas periódicas que indican tendencia anormal, sin falla declarada aún).

**Criterios de aceptación:**
- Cada OT tiene el campo "tipo" fijo con valor: Correctiva | Preventiva | Predictiva. Este campo no puede modificarse una vez creada la OT.
- Las OTs preventivas tienen referencia obligatoria al plan de mantenimiento que las generó; este vínculo queda visible en el detalle de la OT.
- Las OTs predictivas tienen un campo "motivo de generación predictiva" de texto libre, obligatorio al crear la OT, donde el ADMIN documenta la lectura o condición que motivó su creación.
- El tipo de OT se muestra en todos los listados, reportes PDF, y en el dashboard de KPIs.
- El tipo alimenta los cálculos diferenciados de KPIs: el MTTR se calcula solo sobre OTs correctivas; el cumplimiento de planes solo sobre OTs preventivas.
