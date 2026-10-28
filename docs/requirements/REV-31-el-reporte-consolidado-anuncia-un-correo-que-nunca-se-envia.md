---
id: REV-31
issue: 145
titulo: "El reporte consolidado anuncia un correo que nunca se envía"
tipo: bug
prioridad: should-have
modulo: pdf
estado: CLOSED
etiquetas: ['priority: should-have', 'type: bug', 'mod: pdf', 'platform: backend', 'platform: web']
---

# REV-31 - El reporte consolidado anuncia un correo que nunca se envía

### REV-31: El reporte consolidado anuncia un correo que nunca se envía
**Prioridad:** S

**Descripción:**
Al pedir el reporte consolidado la pantalla dice que llegará un correo, pero la tarea no envía nada. Se debe enviar o corregir el mensaje.

**Criterios de aceptación:**
- [ ] La tarea envía el PDF al usuario que lo pidió, o el aviso se cambia para reflejar lo que hace
- [ ] El correo usa plantilla y asunto claros
- [ ] Se maneja el caso sin correo
- [ ] Existe prueba de la tarea
- [ ] El texto de la pantalla coincide con el comportamiento

**Implementación:**
Pendiente. `generate_consolidated_report` en `backend/apps/reports/tasks.py` genera el PDF pero no envía correo; `frontend/src/pages/reports/ReportsPage.jsx` dice «Recibiras un email cuando este listo».

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `pdf`
- Prioridad: `S`
- Fuente: `Desarrollo (sprint de octubre)`
