---
id: REV-16
issue: 112
titulo: "Definir el comportamiento al desactivar activos, ubicaciones y planes"
tipo: functional
prioridad: must-have
modulo: trazabilidad
estado: OPEN
etiquetas: ['priority: must-have', 'type: functional', 'mod: trazabilidad']
---

# REV-16 - Definir el comportamiento al desactivar activos, ubicaciones y planes

### REV-16: Definir el comportamiento al desactivar activos, ubicaciones y planes
**Prioridad:** M

**Descripción:**
El cliente exige que nada se borre al desactivar y que el historial siga consultable. Había que definir qué ocurre con los activos de una ubicación desactivada, con las OT y planes de un activo dado de baja, y con las OT de un plan desactivado.

**Criterios de aceptación:**
- [x] Dar de baja un activo anula sus tareas pendientes y conserva el historial
- [x] Baja y reactivación masiva con reprogramación de tareas
- [x] Un protocolo inactivo deja de generar tareas
- [ ] Regla definida para desactivar una ubicación con activos

**Implementación:**
Baja de equipo anula tareas pendientes (d2a41a7); baja y reactivación masiva con tareas reprogramadas (0a647bf). Los nodos con contenido no se pueden eliminar, pero desactivarlos no tiene efecto sobre sus activos. Archivos: backend/apps/maintenance/services.py, backend/apps/assets/views.py.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `trazabilidad`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
