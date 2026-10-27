---
id: REV-09
issue: 104
titulo: "Permisos por usuario, además de por rol"
tipo: functional
prioridad: must-have
modulo: usuarios-roles
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: usuarios-roles']
---

# REV-09 - Permisos por usuario, además de por rol

### REV-09: Permisos por usuario, además de por rol
**Prioridad:** M

**Descripción:**
Los permisos eran solo por rol, pero el cliente necesita excepciones por persona (por ejemplo un técnico con más permisos que otro, o un instalador sin permisos de checklist).

**Criterios de aceptación:**
- [x] Permisos individuales que se suman a los del rol
- [x] Gestión desde la pantalla de usuarios
- [ ] Restar permisos del rol (hoy solo se suman; por confirmar si se necesita)

**Implementación:**
Campo permisos_extra y selector agrupado por área en la pantalla de usuarios (5ed8863). Archivos: backend/apps/users/serializers.py, frontend/src/pages/users/UsersPage.jsx.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `usuarios-roles`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
