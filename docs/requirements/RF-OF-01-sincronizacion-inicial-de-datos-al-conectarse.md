---
id: RF-OF-01
issue: 46
titulo: "Sincronización inicial de datos al conectarse"
tipo: functional
prioridad: must-have
modulo: offline
estado: OPEN
etiquetas: ['priority: must-have', 'type: functional', 'mod: offline']
---

# RF-OF-01 - Sincronización inicial de datos al conectarse

### RF-OF-01: Sincronización inicial de datos al conectarse
**Prioridad:** M

**Descripción:**
Al iniciar la app con conexión activa, los datos necesarios para trabajar offline se descargan automáticamente al dispositivo del técnico, sin que el técnico deba hacer nada manualmente.

**Criterios de aceptación:**
- Al hacer login con conexión o al recuperar conexión después de un período offline, la app sincroniza en background: todas las OTs del `TEC` en estados Pendiente y En Progreso con sus datos completos (datos del activo, plantilla del checklist, historial básico del activo: últimas 3 OTs completadas), el catálogo de repuestos activos (nombre, código, stock disponible), y los datos del perfil del técnico.
- La sincronización completa para hasta 20 OTs pendientes con checklist y metadatos tarda ≤ 30 segundos en una conexión 4G estándar.
- Las fotos de OTs anteriores NO se descargan al dispositivo (se acceden on-demand cuando hay conexión). Solo se descarga la información textual y de estructura de las OTs.
- La app muestra un indicador de progreso durante la sincronización.
- Si la sincronización falla parcialmente (ej: se pierde conexión a mitad), se completa automáticamente cuando vuelve a haber conexión.

---

---

**Metadatos de importacion**
- Repositorio destino: `sdeossag/TodoGas`
- Modulo: `OF - Modo Offline (App Android)`
- Prioridad: `M`
- Fuente: `CMMS_Fase1_Requisitos_Funcionales.md`

**Implementación (revisión del 2026-10-27):**
- [x] Al entrar o recuperar red, bajar OT Pendiente y En Progreso con activo y plantilla del checklist — downloadOfflineBundles baja todas las OT abiertas y el offline-bundle de cada una; no pide nada al técnico.
- [ ] Historial básico: últimas 3 OT del activo — El paquete no lo incluye.
- [ ] Catálogo de repuestos activos — No se guarda en el teléfono; registrar repuestos exige conexión.
- [x] Datos del perfil del técnico — Se guarda el usuario y su firma (cacheMySignature).
- [ ] ≤30 s con 20 OT en 4G — Baja una OT por petición, sin medición.
- [x] No bajar fotos antiguas — Solo texto y estructura.
- [ ] Indicador de progreso de la descarga — El banner solo muestra la subida; la descarga es silenciosa.
- [x] Completar solo lo parcial al volver la red — Reintento cada 60 s, al volver la app a primer plano y al recuperar red.

Commits: cf64142, 9267bfa, b065c1d
Archivos: `frontend/src/api/workOrders.js`, `frontend/src/hooks/useOfflineWorkOrders.js`, `backend/apps/work_orders/views.py`
