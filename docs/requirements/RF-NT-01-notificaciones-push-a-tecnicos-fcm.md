---
id: RF-NT-01
issue: 56
titulo: "Notificaciones push a técnicos (FCM)"
tipo: functional
prioridad: must-have
modulo: notificaciones
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: notificaciones']
---

# RF-NT-01 - Notificaciones push a técnicos (FCM)

### RF-NT-01: Notificaciones push a técnicos (FCM)
**Prioridad:** M

**Descripción:**
Los técnicos reciben notificaciones push en la app Android para todos los eventos relevantes a sus OTs asignadas, incluso si la app está en background o el dispositivo bloqueado.

**Criterios de aceptación:**
- Las notificaciones push usan **Firebase Cloud Messaging (FCM)**.
- **Eventos que generan notificación push al técnico:**
  - Nueva OT asignada: "Nueva OT asignada: {nombre del activo} — {hospital} | Prioridad: {Alta/Media/Baja}"
  - OT reasignada (se le asigna una que antes no tenía): "OT {número} reasignada a ti: {nombre del activo}"
  - OT devuelta a revisión con rechazo del ADMIN: "OT {número} requiere correcciones: {comentario del ADMIN}"
  - OT próxima a vencer (24 horas antes de la fecha límite): "OT {número} vence mañana: {nombre del activo}"
- Si el técnico está offline, la notificación se encola en FCM y se entrega cuando recupera conexión.
- Al tocar la notificación, la app se abre directamente en el detalle de la OT correspondiente.
- El técnico puede ver el historial de las últimas 50 notificaciones recibidas en una sección de la app.
- Las notificaciones respetan la configuración de notificaciones del sistema operativo Android del dispositivo.
