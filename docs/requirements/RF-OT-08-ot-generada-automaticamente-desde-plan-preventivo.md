---
id: RF-OT-08
issue: 15
titulo: "OT generada automáticamente desde plan preventivo"
tipo: functional
prioridad: must-have
modulo: ordenes-trabajo
estado: OPEN
etiquetas: ['priority: must-have', 'type: functional', 'mod: ordenes-trabajo']
---

# RF-OT-08 - OT generada automáticamente desde plan preventivo

### RF-OT-08: OT generada automáticamente desde plan preventivo
**Prioridad:** M

**Descripción:**
Las OTs preventivas se generan automáticamente por el sistema según la periodicidad de los planes de mantenimiento, sin intervención manual del ADMIN.

**Criterios de aceptación:**
- La generación automática corre como tarea Celery programada al inicio de cada día a las 06:00 AM (hora Colombia, UTC-5).
- Cada OT generada incluye automáticamente: referencia al plan que la originó, activo correspondiente, checklist preconfigurado en el plan, técnico preconfigurado en el plan (si existe), fecha límite calculada según la periodicidad del plan más el buffer configurado.
- Si el plan no tiene técnico preconfigurado, la OT se crea sin técnico asignado y el `ADMIN` recibe alerta inmediata.
- **Protección anti-duplicados:** si ya existe una OT activa (Pendiente / En Progreso / En Revisión) generada desde el mismo plan para el mismo activo, el sistema NO genera una nueva. En cambio, envía una alerta al ADMIN indicando que hay una OT pendiente de ese plan sin completar.
- Las OTs generadas automáticamente tienen un ícono diferenciador en el listado para distinguirlas de las creadas manualmente.
- El sistema registra en el log: fecha/hora de generación, plan origen, activo, resultado (generada / omitida por duplicado con referencia).

---

## MÓDULO PM — Planes de Mantenimiento Preventivo
