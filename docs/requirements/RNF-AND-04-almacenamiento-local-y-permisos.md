---
id: RNF-AND-04
issue: 85
titulo: "Almacenamiento local y permisos"
tipo: non-functional
prioridad: must-have
modulo: android
estado: CLOSED
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: android']
---

# RNF-AND-04 - Almacenamiento local y permisos

### RNF-AND-04: Almacenamiento local y permisos
**Prioridad:** M

**Descripción:**
La app solicita solo los permisos de Android estrictamente necesarios y gestiona el almacenamiento local de forma responsable.

**Criterios de aceptación:**
- **Permisos solicitados en tiempo de ejecución** (Runtime Permissions, Android 6+):
  - `CAMERA`: para capturar fotos de evidencia. Se solicita la primera vez que el técnico intenta tomar una foto, con explicación del porqué.
  - `ACCESS_FINE_LOCATION`: para geolocalización en fotos. Se solicita junto con el permiso de cámara. La app explica al técnico que la ubicación se registra en las fotos de evidencia de las OTs.
  - `INTERNET` y `ACCESS_NETWORK_STATE`: para sincronización. Son permisos normales (no runtime).
- La app **no solicita** permisos de lectura de galería, contactos, ni ningún permiso no relacionado con sus funciones.
- El almacenamiento local (fotos offline + datos de OTs en SQLite) usa el **directorio privado de la app** en el almacenamiento interno del dispositivo (no la galería ni almacenamiento externo). Los datos de la app no son accesibles por otras apps ni visibles en el explorador de archivos del dispositivo.
- El tamaño máximo de datos almacenados localmente (OTs sincronizadas + fotos pendientes de subir) está limitado a **500 MB**. Si se supera, la app alerta al técnico para que sincronice y libere espacio.
- Al cerrar sesión o desinstalar la app, todos los datos locales se eliminan del dispositivo.

---

## RNF-PDF — Generación de Documentos PDF
