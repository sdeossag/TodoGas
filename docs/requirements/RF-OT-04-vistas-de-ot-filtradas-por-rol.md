---
id: RF-OT-04
issue: 11
titulo: "Vistas de OT filtradas por rol"
tipo: functional
prioridad: must-have
modulo: ordenes-trabajo
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: ordenes-trabajo']
---

# RF-OT-04 - Vistas de OT filtradas por rol

### RF-OT-04: Vistas de OT filtradas por rol
**Prioridad:** M

**Descripción:**
Cada rol tiene una vista de OTs filtrada automáticamente según sus permisos de visibilidad, sin posibilidad de ver datos de otros usuarios o clientes.

**Criterios de aceptación:**
- **`ADMIN`:** ve todas las OTs del sistema sin restricción. Filtros disponibles: estado, tipo, hospital, técnico asignado, prioridad, rango de fechas de creación, rango de fechas límite. Puede exportar el listado filtrado a CSV.
- **`TEC`:** ve únicamente las OTs que le han sido asignadas a él. No puede ver OTs de otros técnicos, aunque coincidan en el mismo hospital. El API retorna solo sus OTs incluso si intenta manipular parámetros de la petición.
- **`CLI`:** ve únicamente las OTs en estado "Completada" de los activos de su hospital. No ve OTs en estados intermedios (Pendiente, En Progreso, En Revisión, Cancelada).
- La vista principal al iniciar sesión para cada rol es su lista de OTs activas por defecto.
- **Orden por defecto** del listado: primero OTs con prioridad Alta, luego por fecha límite ascendente (las más urgentes primero).
- El listado muestra columnas: número de OT, tipo, nombre del activo, hospital, estado (con color diferenciador), técnico asignado, fecha límite, e indicador visual de "VENCIDA" si la fecha límite ya pasó y la OT no está completada.
