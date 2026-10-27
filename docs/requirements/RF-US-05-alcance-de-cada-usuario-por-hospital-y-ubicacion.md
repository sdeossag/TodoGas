---
id: RF-US-05
issue: 131
titulo: "Alcance de cada usuario por hospital y ubicación"
tipo: functional
prioridad: must-have
modulo: usuarios-roles, seguridad
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: usuarios-roles', 'mod: seguridad', 'platform: backend', 'platform: web']
---

# RF-US-05 - Alcance de cada usuario por hospital y ubicación

### RF-US-05: Alcance de cada usuario por hospital y ubicación
**Prioridad:** M

**Descripción:**
Cada cuenta debe ver solo lo que le corresponde. Se asigna a cada usuario un hospital o una rama del árbol de ubicaciones y todas las pantallas respetan ese alcance.

**Criterios de aceptación:**
- [x] Se asigna hospital y ubicación a cada usuario desde la pantalla de usuarios
- [x] Equipos, órdenes y evidencias se filtran por ese alcance
- [x] Aplica a todos los roles
- [x] El historial de OT y los protocolos también respetan el alcance
- [x] Las cuentas de hospital no pueden cerrar el checklist

**Implementación:**
Implementado en `286710e` (alcance), `0ea8c21` (pantalla de usuarios) y `5fd3e08` (historial, protocolos y aprobación atómica). Archivos clave: `backend/apps/users/scope.py`, `backend/apps/assets/views.py`, `backend/apps/work_orders/views.py`, `frontend/src/pages/users/UsersPage.jsx`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `usuarios-roles, seguridad`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-10-23)`
