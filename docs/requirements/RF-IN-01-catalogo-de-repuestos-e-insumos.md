---
id: RF-IN-01
issue: 42
titulo: "Catálogo de repuestos e insumos"
tipo: functional
prioridad: must-have
modulo: inventario
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: inventario']
---

# RF-IN-01 - Catálogo de repuestos e insumos

### RF-IN-01: Catálogo de repuestos e insumos
**Prioridad:** M

**Descripción:**
El `ADMIN` gestiona un catálogo centralizado de repuestos e insumos disponibles para las intervenciones de mantenimiento. El catálogo es compartido entre todos los hospitales y técnicos.

**Criterios de aceptación:**
- **Campos por repuesto:** código interno (único, obligatorio), nombre (obligatorio), descripción (opcional), unidad de medida (Unidades / Metros / Litros / Kilogramos / Otro — configurable), stock actual (calculado automáticamente por el sistema según entradas y salidas; no editable directamente), stock mínimo (umbral de alerta, obligatorio), proveedor habitual (texto libre, opcional), precio unitario en COP (opcional, usado para cálculo de costos de OT), estado (activo / inactivo).
- Los repuestos inactivos no aparecen en la selección al crear OTs ni al registrar salidas.
- La búsqueda en el catálogo por nombre o código retorna resultados en ≤ 2 segundos.
- El stock actual no puede ser editado directamente: solo se modifica mediante entradas y salidas registradas formalmente.
- El `ADMIN` puede exportar el catálogo completo con stock actual a CSV.
