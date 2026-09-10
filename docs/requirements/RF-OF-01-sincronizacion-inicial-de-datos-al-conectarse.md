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
