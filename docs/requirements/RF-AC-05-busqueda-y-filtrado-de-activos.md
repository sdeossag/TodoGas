---
id: RF-AC-05
issue: 5
titulo: "Búsqueda y filtrado de activos"
tipo: functional
prioridad: must-have
modulo: activos
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: activos']
---

# RF-AC-05 - Búsqueda y filtrado de activos

### RF-AC-05: Búsqueda y filtrado de activos
**Prioridad:** M

**Descripción:**
Todos los roles pueden buscar activos con búsqueda por texto libre y filtros combinados. Los resultados están restringidos según el rol del usuario. El sistema debe ser performante sobre el universo de ~3,940 activos.

**Criterios de aceptación:**
- La búsqueda por texto libre aplica simultáneamente sobre: nombre, código interno, número de serie, modelo, marca, y nombre del hospital.
- Los filtros disponibles son: hospital, estado del activo, tipo de activo, tipo de gas manejado, rango de fecha de última intervención.
- Los filtros son combinables entre sí; el sistema aplica todos los filtros activos simultáneamente.
- Los resultados se paginan: 50 por página por defecto, configurable a 100.
- El `CLI` ve únicamente activos de su hospital; ningún filtro puede saltar esta restricción.
- El `TEC` ve todos los activos para consulta, pero desde la búsqueda no puede crear ni editar.
- La búsqueda retorna resultados en ≤ 2 segundos sobre el universo completo de activos con los filtros aplicados.
- Desde los resultados se puede acceder directamente a la ficha del activo.
- Si la búsqueda no retorna resultados, el sistema muestra un mensaje descriptivo (no una pantalla vacía sin contexto).
