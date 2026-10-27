---
id: REV-30
issue: 144
titulo: "Quitar la columna «Costo unit.» de los repuestos de la OT"
tipo: chore
prioridad: could-have
modulo: ordenes-trabajo
estado: OPEN
etiquetas: ['priority: could-have', 'type: chore', 'mod: ordenes-trabajo', 'platform: web']
---

# REV-30 - Quitar la columna «Costo unit.» de los repuestos de la OT

### REV-30: Quitar la columna «Costo unit.» de los repuestos de la OT
**Prioridad:** C

**Descripción:**
El cliente decidió no llevar costos en la orden de trabajo. Se quita la columna de costo unitario en los repuestos.

**Criterios de aceptación:**
- [ ] La tabla de repuestos de la OT no muestra «Costo unit.»
- [ ] No se muestran totales de costo
- [ ] La captura de repuestos sigue funcionando
- [ ] El PDF no muestra costos
- [ ] Sin errores en consola

**Implementación:**
Pendiente. La columna está en `frontend/src/pages/work-orders/WorkOrderDetailPage.jsx` (encabezado «Costo unit.»).

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `ordenes-trabajo`
- Prioridad: `C`
- Fuente: `Revisión con el cliente (2026-10-23)`
