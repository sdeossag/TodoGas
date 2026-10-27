---
id: RF-PDF-04
issue: 135
titulo: "Reenvío de varias actas por correo con los PDF adjuntos"
tipo: functional
prioridad: should-have
modulo: pdf, notificaciones
estado: CLOSED
etiquetas: ['priority: should-have', 'type: functional', 'mod: pdf', 'mod: notificaciones', 'platform: backend', 'platform: web']
---

# RF-PDF-04 - Reenvío de varias actas por correo con los PDF adjuntos

### RF-PDF-04: Reenvío de varias actas por correo con los PDF adjuntos
**Prioridad:** S

**Descripción:**
Se pueden seleccionar varias actas y reenviarlas por correo con los PDF adjuntos. Se manda un correo por hospital y los adjuntos se reparten en lotes de 20 MB.

**Criterios de aceptación:**
- [x] Se pueden seleccionar varias actas para reenviar
- [x] Se envía un correo por hospital
- [x] Los PDF van adjuntos
- [x] Los adjuntos se reparten en lotes de 20 MB
- [x] El correo usa una plantilla propia

**Implementación:**
Implementado en `6c2cef8`. Archivos clave: `backend/apps/reports/tasks.py`, `backend/apps/reports/views.py`, `backend/apps/reports/serializers.py`, `backend/apps/reports/templates/reports/email_reports_bundle.html`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `pdf, notificaciones`
- Prioridad: `S`
- Fuente: `Desarrollo (sprint de octubre)`
