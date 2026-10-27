---
id: RF-OF-02
issue: 47
titulo: "Ejecución completa de OT en modo offline"
tipo: functional
prioridad: must-have
modulo: offline
estado: OPEN
etiquetas: ['priority: must-have', 'type: functional', 'mod: offline']
---

# RF-OF-02 - Ejecución completa de OT en modo offline

### RF-OF-02: Ejecución completa de OT en modo offline
**Prioridad:** M

**Descripción:**
El técnico puede ejecutar completamente una OT previa sincronizada sin necesidad de conexión a internet. Todas las acciones se guardan localmente y se sincronizan al recuperar conexión.

**Criterios de aceptación:**
- En modo offline, están disponibles: ver el listado de OTs sincronizadas, ver el detalle de cada OT, cambiar el estado a "En Progreso", completar todos los campos del checklist, capturar fotos (almacenadas localmente en el dispositivo hasta sincronizar), registrar firma del técnico, registrar firma del receptor con nombre y cargo, registrar repuestos usados (del catálogo descargado), añadir observaciones de texto libre.
- Las fotos se almacenan en el almacenamiento interno del dispositivo mientras no se sincronizan. La app muestra cuántas fotos pendientes de subir hay.
- La geolocalización se captura del GPS del dispositivo (no requiere internet). Si el GPS no tiene señal, se marca "GPS no disponible" como se especifica en RF-EV-01.
- El progreso del checklist se guarda automáticamente en SQLite cada 30 segundos. Si la app se cierra inesperadamente, al reabrirla el técnico retoma exactamente desde donde quedó.
- El técnico **no puede enviar la OT a revisión mientras está offline.** El botón está deshabilitado con el mensaje: "Sin conexión. Conectate para enviar la OT a revisión." Esta restricción evita inconsistencias con el estado en el servidor.
- El técnico no puede crear nuevas OTs en modo offline.

---

---

**Metadatos de importacion**
- Repositorio destino: `sdeossag/TodoGas`
- Modulo: `OF - Modo Offline (App Android)`
- Prioridad: `M`
- Fuente: `CMMS_Fase1_Requisitos_Funcionales.md`

**Implementación (revisión del 2026-10-27):**
- [x] Ver listado y detalle, pasar a En Progreso, llenar el checklist — SQLite: offline_work_orders, respuestas y estado local.
- [x] Fotos guardadas en el teléfono — photoQueue.js y offline_photos; la pantalla cuenta lo pendiente en elementos, no solo fotos.
- [x] Firma del técnico y del receptor con nombre y cargo — offline_signatures con signer_name y signer_role.
- [ ] Registrar repuestos del catálogo descargado — RepuestoModal necesita conexión; no hay catálogo local.
- [x] Observaciones de texto libre — Pendientes y respuestas guardados sin red.
- [x] GPS sin internet; marcar GPS no disponible — Latitud y longitud en fotos y firmas.
- [x] Guardado automático cada 30 s — Se guarda en cada cambio, con lo que supera el requisito.
- [ ] ~~No enviar a revisión sin conexión~~ (ya no aplica: Superado: la app permite enviar a revisión y aprobar sin red y se sincroniza después (f57ddb2).)
- [x] No crear OT sin conexión — La creación de OT exige conexión.

Commits: f57ddb2, 5e92475, b065c1d, 334d516
Archivos: `frontend/src/db/schema.js`, `frontend/src/components/workOrders/TransitionButton.jsx`, `frontend/src/pages/work-orders/WorkOrderDetailPage.jsx`
