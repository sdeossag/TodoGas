---
id: RF-IN-02
issue: 43
titulo: "Registro de entradas de stock"
tipo: functional
prioridad: must-have
modulo: inventario
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: inventario']
---

# RF-IN-02 - Registro de entradas de stock

### RF-IN-02: Registro de entradas de stock
**Prioridad:** M

**Descripción:**
El `ADMIN` registra las compras y entradas de stock con trazabilidad completa de cada movimiento.

**Criterios de aceptación:**
- Desde la vista del catálogo, el `ADMIN` puede registrar una entrada de stock para cualquier repuesto activo.
- **Campos de una entrada:** repuesto, cantidad (número positivo, obligatorio), fecha de la entrada, proveedor (texto libre, opcional), número de factura o referencia (texto libre, opcional), observaciones (texto libre, opcional).
- Al guardar la entrada, el stock actual del repuesto se incrementa en la cantidad indicada automáticamente.
- La entrada queda registrada en el historial del repuesto como un movimiento con: tipo "Entrada", cantidad, stock resultante, usuario que la registró, fecha, referencia.
- No existe límite de stock máximo.
