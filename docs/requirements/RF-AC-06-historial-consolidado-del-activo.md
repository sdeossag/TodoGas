---
id: RF-AC-06
issue: 6
titulo: "Historial consolidado del activo"
tipo: functional
prioridad: must-have
modulo: activos
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: activos']
---

# RF-AC-06 - Historial consolidado del activo

### RF-AC-06: Historial consolidado del activo
**Prioridad:** M

**Descripción:**
Cada activo tiene un historial completo, cronológico e inmutable de todas las intervenciones y cambios desde su creación en el sistema. Es el registro maestro del activo para efectos de auditoría.

**Criterios de aceptación:**
- El historial incluye: todas las OTs ejecutadas (correctivas, preventivas, predictivas) con fecha de creación, fecha de cierre, técnico ejecutor, estado, y enlace al PDF del reporte.
- Incluye cambios de estado del activo (activo → en mantenimiento → activo, etc.) con fecha y responsable.
- Incluye modificaciones a la ficha técnica (qué campo cambió, valor anterior, valor nuevo, quién lo cambió).
- El historial es inmutable: ningún rol puede editar, ocultar ni eliminar entradas.
- Se puede filtrar el historial por: tipo de evento (OT correctiva / preventiva / predictiva / cambio de estado / cambio de datos), rango de fechas, y técnico.
- `ADMIN` y `SUP` ven el historial completo incluyendo cambios de datos. `TEC` ve solo las OTs de sus intervenciones propias en ese activo. `CLI` ve únicamente las OTs completadas de sus activos.
- El historial puede exportarse como PDF consolidado del activo completo (útil para auditorías o cuando un cliente solicita el expediente completo).
