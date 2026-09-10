---
id: RF-OT-06
issue: 13
titulo: "Asignación y reasignación de técnico"
tipo: functional
prioridad: must-have
modulo: ordenes-trabajo
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: ordenes-trabajo']
---

# RF-OT-06 - Asignación y reasignación de técnico

### RF-OT-06: Asignación y reasignación de técnico
**Prioridad:** M

**Descripción:**
El `ADMIN` tiene control total sobre la asignación de técnicos a OTs, con notificación automática a los involucrados y registro del histórico de asignaciones.

**Criterios de aceptación:**
- Solo `ADMIN` puede asignar o reasignar el técnico de una OT.
- La reasignación es posible en estados: Pendiente, En Progreso, En Revisión. No es posible en estado Completada ni Cancelada.
- Al reasignar: el nuevo técnico recibe notificación push y correo con detalle de la OT; el técnico anterior recibe notificación de que la OT le fue reasignada.
- El sistema registra el historial completo de asignaciones de la OT: técnico original, fecha de asignación original, técnico nuevo, fecha de reasignación, motivo (campo opcional para el ADMIN).
- Una OT solo puede tener un técnico asignado a la vez (no asignación múltiple).
- Si se crea una OT sin técnico asignado (campo opcional en el formulario), el ADMIN recibe una alerta y la OT aparece en el listado como "Sin asignar" con color diferenciador.
