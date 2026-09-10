---
id: RNF-SEG-01
issue: 66
titulo: "Seguridad en el transporte de datos"
tipo: non-functional
prioridad: must-have
modulo: seguridad
estado: CLOSED
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: seguridad']
---

# RNF-SEG-01 - Seguridad en el transporte de datos

### RNF-SEG-01: Seguridad en el transporte de datos
**Prioridad:** M

**Descripción:**
Todas las comunicaciones entre clientes (web, app) y el servidor deben estar cifradas en tránsito. No se permite tráfico en texto claro bajo ninguna circunstancia.

**Criterios de aceptación:**
- **HTTPS obligatorio** en todos los endpoints del API y en el frontend web. Las peticiones HTTP son redirigidas automáticamente a HTTPS con código 301.
- **TLS 1.2 mínimo** en todas las conexiones. TLS 1.0 y 1.1 están deshabilitados en el servidor.
- Los certificados SSL/TLS se gestionan mediante **AWS Certificate Manager** (renovación automática, sin expiración manual).
- La app Android usa exclusivamente HTTPS para todas las peticiones al API. El APK tiene **Network Security Config** configurado para rechazar conexiones HTTP en producción.
- Los tokens JWT se transmiten únicamente en el header `Authorization: Bearer {token}`, nunca en URLs ni en query parameters.
- Las URLs pre-firmadas de S3 (para acceder a fotos y PDFs) tienen expiración de 24 horas y no son navegables públicamente sin el token de firma.
