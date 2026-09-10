---
id: RF-NT-02
issue: 57
titulo: "Alertas por correo al ADMIN"
tipo: functional
prioridad: must-have
modulo: notificaciones
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: notificaciones']
---

# RF-NT-02 - Alertas por correo al ADMIN

### RF-NT-02: Alertas por correo al ADMIN
**Prioridad:** M

**Descripción:**
El `ADMIN` recibe alertas por correo electrónico agrupadas y organizadas para los eventos críticos del sistema que requieren su atención.

**Criterios de aceptación:**
- **Alertas inmediatas** (correo individual tan pronto ocurre el evento):
  - OT pasa a estado "En Revisión" (requiere su aprobación para completar): asunto "OT en revisión: {número} | {activo} — {hospital}"
  - Fallo definitivo en el envío de PDF a un cliente (tras 3 reintentos): asunto "Error: no se pudo enviar PDF de OT {número} a {hospital}"
  - OT preventiva generada automáticamente sin técnico asignado.
- **Alertas diarias** (un solo correo consolidado a las 08:00 AM con todos los eventos del tipo):
  - OTs vencidas del día anterior (agrupadas en un único correo con la lista completa).
  - Repuestos con stock bajo el mínimo (agrupados en un único correo).
- El `ADMIN` puede configurar desde la interfaz cuáles tipos de alerta desea recibir por correo (activar/desactivar individualmente por tipo de alerta).
- Los correos de alerta no se envían repetidamente por el mismo evento si el estado no cambia (ej: una OT vencida que sigue vencida al día siguiente genera solo una nueva entrada en el correo diario, no correos repetidos).
