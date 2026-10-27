---
id: REV-10
issue: 105
titulo: "El administrador debe poder iniciar y diligenciar checklists"
tipo: functional
prioridad: must-have
modulo: usuarios-roles
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: usuarios-roles']
---

# REV-10 - El administrador debe poder iniciar y diligenciar checklists

### REV-10: El administrador debe poder iniciar y diligenciar checklists
**Prioridad:** M

**Descripción:**
Solo el técnico asignado podía iniciar el checklist, pero hay trabajo que el área de mantenimiento no cubre y el administrador debe reportarlo. Se necesita que administrador y supervisor inicien y respondan checklists dejando trazabilidad.

**Criterios de aceptación:**
- [x] Administrador y supervisor pueden iniciar y responder checklists
- [x] Queda registrado quién diligenció cada respuesta

**Implementación:**
La OT puede asignarse a un administrador o supervisor, que la ejecuta y envía a revisión como un técnico (cdaa4f3). Archivos: backend/apps/users/scope.py, backend/apps/checklists/views.py.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `usuarios-roles`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
