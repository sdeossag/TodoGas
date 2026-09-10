---
id: RF-IN-04
issue: 45
titulo: "Alertas de stock mínimo"
tipo: functional
prioridad: must-have
modulo: inventario
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: inventario']
---

# RF-IN-04 - Alertas de stock mínimo

### RF-IN-04: Alertas de stock mínimo
**Prioridad:** M

**Descripción:**
El sistema alerta automáticamente al ADMIN cuando el stock de un repuesto alcanza o cae por debajo del stock mínimo configurado.

**Criterios de aceptación:**
- El dashboard del `ADMIN` tiene una sección permanente de "Alertas de inventario" que lista todos los repuestos con stock ≤ stock mínimo configurado.
- Por cada repuesto en alerta se muestra: nombre, stock actual, stock mínimo, diferencia (cuántas unidades faltan para alcanzar el mínimo), proveedor habitual si está configurado.
- El `ADMIN` recibe un correo de alerta cuando el stock de un repuesto cae al nivel mínimo o por debajo. Este correo se envía máximo una vez por repuesto por día (no en cada movimiento que genere la alerta).
- El correo agrupa todas las alertas del día en un solo mensaje (no uno por repuesto).

---

## MÓDULO OF — Modo Offline (App Android)
