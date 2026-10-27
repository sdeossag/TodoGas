---
id: RF-HA-01
issue: 123
titulo: "Registro de hallazgos desde campo, también sin red"
tipo: functional
prioridad: must-have
modulo: hallazgos
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'platform: backend', 'platform: android', 'mod: hallazgos']
---

# RF-HA-01 - Registro de hallazgos desde campo, también sin red

### RF-HA-01: Registro de hallazgos desde campo, también sin red
**Prioridad:** M

**Descripción:**
Durante un mantenimiento el técnico puede encontrar un problema distinto al de la tarea. Puede registrarlo como hallazgo con datos esenciales y fotos, indicando si lo resolvió en sitio o queda pendiente, aunque no tenga conexión.

**Criterios de aceptación:**
- [x] El técnico crea un hallazgo desde la orden de trabajo
- [x] Indica si quedó resuelto en sitio o pendiente y los datos esenciales
- [x] Puede adjuntar fotos, con ubicación GPS cuando está disponible
- [x] Sin red el hallazgo se guarda en el teléfono y se sincroniza después
- [x] El hallazgo queda vinculado al equipo y a la orden

**Implementación:**
Implementado en `c2f8f21` (modelo, API y fotos de hallazgo) y `7a6bc4e` (cola sin red en el teléfono y fotos con GPS). Archivos clave: `backend/apps/evidence/models.py`, `backend/apps/work_orders/views.py`, `frontend/src/api/findings.js`, `frontend/src/components/findings/FindingsPanel.jsx`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `hallazgos`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-10-23)`
