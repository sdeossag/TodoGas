---
id: REV-06
issue: 101
titulo: "Seleccionar activos filtrando por ubicación al crear una OT"
tipo: functional
prioridad: must-have
modulo: ordenes-trabajo
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: ordenes-trabajo']
---

# REV-06 - Seleccionar activos filtrando por ubicación al crear una OT

### REV-06: Seleccionar activos filtrando por ubicación al crear una OT
**Prioridad:** M

**Descripción:**
Con muchos activos y nombres repetidos, buscar por nombre no sirve. Se pidió filtrar por ubicación a cualquier nivel del árbol, seleccionar en bloque y filtrar el listado de OT por ubicación y activo.

**Criterios de aceptación:**
- [x] Filtro por ubicación a cualquier nivel al crear la OT
- [x] Selección múltiple de los activos filtrados
- [x] Listado de OT filtrable por hospital, ubicación y activo

**Implementación:**
Selector por ubicación con subniveles en la OT manual (804f2c5) y filtros del listado de OT por hospital, ubicación y activo, guardados en la URL (9e29c15).

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `ordenes-trabajo`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
