---
id: RF-PM-04
issue: 19
titulo: "Edición y desactivación de planes"
tipo: functional
prioridad: should-have
modulo: planes-pm
estado: CLOSED
etiquetas: ['priority: should-have', 'type: functional', 'mod: planes-pm']
---

# RF-PM-04 - Edición y desactivación de planes

### RF-PM-04: Edición y desactivación de planes
**Prioridad:** S

**Descripción:**
El `ADMIN` puede modificar planes existentes con control sobre el impacto en las OTs ya generadas. Existe control de versiones del plan.

**Criterios de aceptación:**
- Al editar un plan con OTs pendientes generadas desde él, el sistema advierte y presenta dos opciones: (1) dejar las OTs existentes sin cambios, (2) actualizar las OTs pendientes con los nuevos parámetros (técnico, checklist, fecha límite).
- Al cambiar la frecuencia del plan, el sistema recalcula las próximas fechas a partir de la última ejecución completada real (no desde la fecha del cambio).
- Al pausar un plan, las OTs futuras programadas (no generadas aún) dejan de generarse. Las OTs ya creadas y pendientes permanecen activas para que el técnico las complete.
- Si el ADMIN quiere cancelar las OTs pendientes al pausar el plan, existe una opción explícita adicional para hacerlo en bloque (con motivo obligatorio).
- El sistema mantiene un historial de versiones del plan: cuándo se modificó, qué campos cambiaron, quién lo modificó.

---

## MÓDULO CK — Checklists Dinámicos
