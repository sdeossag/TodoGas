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
