---
id: RF-AC-09
issue: 130
titulo: "Baja y reactivación masiva de activos"
tipo: functional
prioridad: should-have
modulo: activos
estado: CLOSED
etiquetas: ['priority: should-have', 'type: functional', 'mod: activos', 'platform: backend', 'platform: web']
---

# RF-AC-09 - Baja y reactivación masiva de activos

### RF-AC-09: Baja y reactivación masiva de activos
**Prioridad:** S

**Descripción:**
Dar de baja o reactivar equipos uno por uno es lento. Se pueden seleccionar varios y cambiar su estado; al dar de baja se anulan sus tareas pendientes y al reactivar se reprograman.

**Criterios de aceptación:**
- [x] Se puede dar de baja o reactivar varios activos a la vez
- [x] La baja anula las tareas pendientes del equipo
- [x] La reactivación reprograma desde hoy o según el último mantenimiento
- [x] Existe un modal para elegir la opción de reprogramación
- [x] El cambio también funciona desde la ficha de un equipo

**Implementación:**
Implementado en `d2a41a7` (baja que anula tareas) y `0a647bf` (masivo y reprogramación). Archivos clave: `backend/apps/assets/views.py`, `backend/apps/maintenance/services.py`, `frontend/src/components/assets/EstadoMasivoModal.jsx`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `activos`
- Prioridad: `S`
- Fuente: `Desarrollo (sprint de octubre)`
