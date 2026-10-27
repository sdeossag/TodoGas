---
id: REV-03
issue: 98
titulo: "Una OT debe poder cubrir varios activos, cada uno con su protocolo"
tipo: functional
prioridad: must-have
modulo: ordenes-trabajo
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: ordenes-trabajo']
---

# REV-03 - Una OT debe poder cubrir varios activos, cada uno con su protocolo

### REV-03: Una OT debe poder cubrir varios activos, cada uno con su protocolo
**Prioridad:** M

**Descripción:**
Una OT apuntaba a un único activo, por lo que atender un servicio completo exigía una OT por equipo. Se pidió elegir una ubicación, seleccionar los activos y generar una sola OT donde cada activo conserve su protocolo, revisando acta, progreso y cierre.

**Criterios de aceptación:**
- [x] Una OT agrupa varias tareas/activos
- [x] Cada activo conserva su checklist
- [x] El acta muestra un cuadro por activo
- [x] Progreso y cierre consideran todas las tareas

**Implementación:**
La OT pasó a ejecutarse con varias tareas (Task.work_order) y existe la OT manual con selección de activos por ubicación (804f2c5). El acta muestra un cuadro por activo (6e45d14) y la ubicación de la visita viaja con la OT (5ed8863).

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `ordenes-trabajo`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
