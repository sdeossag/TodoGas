---
id: RF-HA-02
issue: 124
titulo: "Bandeja del planificador y aviso al hospital por hallazgo crítico"
tipo: functional
prioridad: must-have
modulo: notificaciones, hallazgos
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: notificaciones', 'platform: backend', 'platform: web', 'mod: hallazgos']
---

# RF-HA-02 - Bandeja del planificador y aviso al hospital por hallazgo crítico

### RF-HA-02: Bandeja del planificador y aviso al hospital por hallazgo crítico
**Prioridad:** M

**Descripción:**
Los hallazgos pendientes deben llegar a quien planifica para darles seguimiento, y el hospital debe poder verlos. Si un hallazgo es crítico, se avisa por correo al hospital.

**Criterios de aceptación:**
- [x] Existe una bandeja del planificador con los hallazgos pendientes
- [x] Los hallazgos se pueden filtrar y cambiar de estado
- [x] El hospital ve los hallazgos de sus equipos
- [x] Un hallazgo crítico envía correo al contacto del hospital y a sus usuarios con alcance
- [x] La pestaña de hallazgos aparece en la orden de trabajo

**Implementación:**
Implementado en `2a90673` (pestaña de hallazgos, bandeja y vista del hospital) y `c2f8f21` (aviso por correo). Archivos clave: `backend/apps/assets/views.py`, `backend/apps/reports/tasks.py`, `frontend/src/components/findings/FindingsPanel.jsx`, `frontend/src/api/findings.js`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `hallazgos, notificaciones`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-10-23)`
