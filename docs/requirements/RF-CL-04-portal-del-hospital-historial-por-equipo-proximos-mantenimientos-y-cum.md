---
id: RF-CL-04
issue: 134
titulo: "Portal del hospital: historial por equipo, próximos mantenimientos y cumplimiento"
tipo: functional
prioridad: must-have
modulo: portal-cliente
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: portal-cliente', 'platform: backend', 'platform: web']
---

# RF-CL-04 - Portal del hospital: historial por equipo, próximos mantenimientos y cumplimiento

### RF-CL-04: Portal del hospital: historial por equipo, próximos mantenimientos y cumplimiento
**Prioridad:** M

**Descripción:**
El personal biomédico del hospital quiere ver el estado de sus equipos sin pedirlo. El portal muestra el historial por equipo, los próximos mantenimientos y el cumplimiento.

**Criterios de aceptación:**
- [x] El portal lista los equipos del hospital
- [x] Cada equipo muestra su historial de tareas
- [x] Se ven los próximos mantenimientos
- [x] Se muestra el cumplimiento
- [x] El historial tiene tipo de tarea y filtro por preventivo, correctivo u otro

**Implementación:**
Implementado en `fa7c469` (historial, próximos y cumplimiento) y `ba517d2` (tipo y filtro). Archivos clave: `backend/apps/assets/views.py`, `frontend/src/pages/assets/MisActivosPage.jsx`, `frontend/src/pages/client/ClientAssetPage.jsx`, `frontend/src/utils/tiposDeTarea.js`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `portal-cliente`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-10-23)`
