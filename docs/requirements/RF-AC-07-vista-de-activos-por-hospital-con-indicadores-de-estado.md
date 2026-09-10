---
id: RF-AC-07
issue: 7
titulo: "Vista de activos por hospital con indicadores de estado"
tipo: functional
prioridad: must-have
modulo: activos
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: activos']
---

# RF-AC-07 - Vista de activos por hospital con indicadores de estado

### RF-AC-07: Vista de activos por hospital con indicadores de estado
**Prioridad:** M

**Descripción:**
El `ADMIN` y `SUP` tienen una vista organizada por hospital que muestra el estado de salud del mantenimiento de cada activo de forma visual e inmediata.

**Criterios de aceptación:**
- La vista principal agrupa activos por hospital, con conteo total de activos por hospital visible sin expandir.
- Al expandir un hospital, se listan sus activos con un indicador de color por activo:
  - 🟢 **Verde:** al día (próximo mantenimiento en más de 15 días, sin OTs vencidas).
  - 🟡 **Amarillo:** próximo vencimiento (mantenimiento programado en ≤ 15 días).
  - 🔴 **Rojo:** con mantenimiento vencido (fecha de ejecución ya pasó y no hay OT completada) o con OT correctiva abierta sin atender por más de 48 horas.
- Cada activo en el listado muestra: nombre, código, tipo, fecha del último mantenimiento, fecha del próximo mantenimiento programado.
- Se puede acceder a la ficha completa del activo desde esta vista con un solo clic.
- La vista tiene un filtro rápido para mostrar solo los activos en estado amarillo o rojo (vista de "activos con atención requerida").

---

## MÓDULO OT — Órdenes de Trabajo
