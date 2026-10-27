---
id: RF-EV-03
issue: 138
titulo: "Fotos sin límite y galería con carga diferida"
tipo: functional
prioridad: must-have
modulo: evidencia
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: evidencia', 'platform: web', 'platform: android']
---

# RF-EV-03 - Fotos sin límite y galería con carga diferida

### RF-EV-03: Fotos sin límite y galería con carga diferida
**Prioridad:** M

**Descripción:**
Subir muchas fotos bloqueaba el envío a revisión. Ahora no hay bloqueos, las fotos pesadas se comprimen y la galería carga las imágenes a medida que se ven.

**Criterios de aceptación:**
- [x] El envío a revisión no se bloquea por fotos
- [x] La galería carga de forma diferida
- [x] La cola sin red no carga todas las imágenes
- [x] Las fotos pesadas se comprimen
- [x] Hay tope de reintentos con aviso

**Implementación:**
Implementado en `b065c1d` (galería y cola) y `0a360e0` (compresión, reintentos y descarga del QR). Archivos clave: `frontend/src/components/evidence/PhotoGallery.jsx`, `frontend/src/db/photoQueue.js`, `frontend/src/hooks/useReviewRequirements.js`, `frontend/src/db/repositories.js`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `evidencia`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-10-23)`
