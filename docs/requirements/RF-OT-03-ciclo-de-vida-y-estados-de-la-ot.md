---
id: RF-OT-03
issue: 10
titulo: "Ciclo de vida y estados de la OT"
tipo: functional
prioridad: must-have
modulo: ordenes-trabajo
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: ordenes-trabajo']
---

# RF-OT-03 - Ciclo de vida y estados de la OT

### RF-OT-03: Ciclo de vida y estados de la OT
**Prioridad:** M

**Descripción:**
Las OTs siguen un ciclo de vida controlado con estados definidos y transiciones restringidas por rol. Cada transición queda registrada de forma inmutable.

**Criterios de aceptación:**

**Estados posibles y transiciones:**
```
Pendiente ──► En Progreso ──► En Revisión ──► Completada
    │              │               │
    └──────────────┴───────────────┴──► Cancelada
```

- **Pendiente → En Progreso:** solo el `TEC` asignado puede iniciar la OT desde la app. Registra fecha y hora de inicio real (puede diferir de la de creación).
- **En Progreso → En Revisión:** solo el `TEC` asignado puede enviar la OT a revisión. **Requisitos bloqueantes previos:** (1) al menos un campo de checklist completado si la OT tiene checklist asociado, (2) al menos 1 foto de evidencia con geolocalización, (3) firma del técnico capturada. Si alguno falta, el sistema bloquea la transición y lista exactamente qué falta.
- **En Revisión → Completada:** solo `ADMIN` o `SUP`. Al completar: se genera el PDF automáticamente, se activa el envío por correo al cliente.
- **En Revisión → En Progreso:** solo `ADMIN`, requiere un comentario de rechazo obligatorio que queda visible para el técnico.
- **Cualquier estado activo → Cancelada:** solo `ADMIN`, requiere motivo de cancelación obligatorio (texto libre). Al cancelar: se revierten las salidas de inventario asociadas, se cancela el envío pendiente de PDF.
- Ninguna transición puede retroceder un estado completado. Una OT en "Completada" o "Cancelada" no puede cambiar de estado bajo ninguna circunstancia.
- Cada cambio de estado se registra en el log de trazabilidad con: usuario que realizó la transición, estado anterior, estado nuevo, fecha/hora UTC exacta, comentarios si aplica.
