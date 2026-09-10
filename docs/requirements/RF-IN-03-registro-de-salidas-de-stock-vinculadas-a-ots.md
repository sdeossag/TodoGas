---
id: RF-IN-03
issue: 44
titulo: "Registro de salidas de stock vinculadas a OTs"
tipo: functional
prioridad: must-have
modulo: inventario
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: inventario']
---

# RF-IN-03 - Registro de salidas de stock vinculadas a OTs

### RF-IN-03: Registro de salidas de stock vinculadas a OTs
**Prioridad:** M

**Descripción:**
Las salidas de inventario se registran principalmente cuando el técnico reporta el uso de repuestos en una OT. También existen ajustes manuales de inventario por el ADMIN.

**Criterios de aceptación:**
- **Salidas desde OT:** durante la ejecución de una OT (en la app), el `TEC` puede agregar repuestos usados seleccionando del catálogo de repuestos activos con cantidad utilizada. Esta acción genera la salida de inventario al completarse la OT (no al seleccionarlos durante la ejecución, para evitar descuentos prematuros si la OT se cancela).
- **Salidas manuales (ajustes):** el `ADMIN` puede registrar salidas manuales de inventario (pérdida, daño, uso no vinculado a OT) con motivo obligatorio y referencia.
- El sistema no permite registrar salidas que lleven el stock por debajo de cero. Si el técnico selecciona más cantidad que el stock disponible, el sistema le alerta y bloquea la operación.
- Si una OT se cancela después de haberse registrado repuestos como usados, la salida de inventario se revierte automáticamente con nota "Revertido por cancelación de OT-{número}".
- Cada salida queda en el historial del repuesto: tipo "Salida", cantidad, stock resultante, referencia (número de OT o "Ajuste manual"), usuario, fecha.
