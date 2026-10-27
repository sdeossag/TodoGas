---
id: RF-OF-04
issue: 137
titulo: "Aprobación y cambios de estado sin red con la hora del teléfono"
tipo: functional
prioridad: must-have
modulo: offline
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: offline', 'platform: backend', 'platform: android']
---

# RF-OF-04 - Aprobación y cambios de estado sin red con la hora del teléfono

### RF-OF-04: Aprobación y cambios de estado sin red con la hora del teléfono
**Prioridad:** M

**Descripción:**
El supervisor puede aprobar sin conexión; se guarda la hora del teléfono y, si al sincronizar el servidor la rechaza, la OT vuelve a revisión con el motivo.

**Criterios de aceptación:**
- [x] Se puede aprobar sin red
- [x] Se guarda la hora real del teléfono
- [x] Al sincronizar se valida la aprobación
- [x] Un rechazo devuelve la OT a revisión con el motivo
- [x] El usuario ve un aviso de atención

**Implementación:**
Implementado en `f57ddb2`. Archivos clave: `backend/apps/work_orders/transitions.py`, `backend/apps/work_orders/views.py`, `frontend/src/components/workOrders/TransitionButton.jsx`, `frontend/src/components/ui/SyncAttentionNotice.jsx`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `offline`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-10-23)`
