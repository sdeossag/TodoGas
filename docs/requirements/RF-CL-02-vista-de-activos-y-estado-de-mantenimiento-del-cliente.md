---
id: RF-CL-02
issue: 50
titulo: "Vista de activos y estado de mantenimiento del cliente"
tipo: functional
prioridad: must-have
modulo: portal-cliente
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: portal-cliente']
---

# RF-CL-02 - Vista de activos y estado de mantenimiento del cliente

### RF-CL-02: Vista de activos y estado de mantenimiento del cliente
**Prioridad:** M

**Descripción:**
El cliente ve el listado de sus activos con indicadores de estado de mantenimiento, acceso a la ficha técnica y al historial de intervenciones.

**Criterios de aceptación:**
- El listado de activos del `CLI` muestra: todos los activos de su hospital (organizados por área/ubicación), con indicadores de estado de mantenimiento (al día / próximo vencimiento / con mantenimiento vencido) iguales a los del ADMIN.
- Al acceder a la ficha de un activo, el `CLI` ve: nombre, código, tipo, número de serie, área de ubicación, fecha de instalación, próximo mantenimiento programado, y fecha del último mantenimiento completado.
- El `CLI` no ve: código interno del sistema, campos de costo, campos de configuración interna, ni el log de auditoría.
- Desde la ficha del activo, el `CLI` puede acceder al historial de OTs completadas de ese activo.
- El `CLI` puede buscar sus activos por nombre, área o tipo.
