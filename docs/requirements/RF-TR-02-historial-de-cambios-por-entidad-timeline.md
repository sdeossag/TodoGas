---
id: RF-TR-02
issue: 33
titulo: "Historial de cambios por entidad (timeline)"
tipo: functional
prioridad: must-have
modulo: trazabilidad
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: trazabilidad']
---

# RF-TR-02 - Historial de cambios por entidad (timeline)

### RF-TR-02: Historial de cambios por entidad (timeline)
**Prioridad:** M

**Descripción:**
Las entidades principales del sistema (Activos, OTs, Planes, Checklists) muestran un timeline de cambios directamente en su vista de detalle, sin necesidad de consultar el log general.

**Criterios de aceptación:**
- El timeline muestra los últimos 50 eventos de esa entidad específica, paginable hacia atrás sin límite.
- Cada entrada del timeline muestra: fecha/hora (en hora local Colombia), nombre del usuario, descripción del cambio en lenguaje natural (ej: "Cambió el estado de 'Pendiente' a 'En Progreso'", "Modificó el campo 'Número de serie' de '123' a '456'", "Añadió foto de evidencia").
- **`ADMIN` y `SUP`:** ven el timeline completo de cualquier entidad, incluyendo cambios de datos técnicos.
- **`TEC`:** ve el timeline solo de las OTs asignadas a él.
- **`CLI`:** no ve el timeline de ninguna entidad.
- El timeline de la OT incluye específicamente: creación, asignaciones/reasignaciones de técnico, cada cambio de estado con el usuario y hora, adición de cada foto (sin mostrar la foto, solo el evento), captura de cada firma, generación del PDF, cada envío del PDF al cliente con resultado.
