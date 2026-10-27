---
id: REV-07
issue: 102
titulo: "Historial de intervenciones por activo, con regeneración del acta"
tipo: functional
prioridad: must-have
modulo: trazabilidad
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: trazabilidad']
---

# REV-07 - Historial de intervenciones por activo, con regeneración del acta

### REV-07: Historial de intervenciones por activo, con regeneración del acta
**Prioridad:** M

**Descripción:**
La pestaña de historial era un marcador de posición. Por auditoría y operación diaria se necesita ver qué se le hizo a cada equipo y cuándo, con acceso al acta y poder regenerar el PDF.

**Criterios de aceptación:**
- [x] Listado de intervenciones del activo ordenado por fecha, con tipo y estado
- [x] Filtro por preventivo, correctivo u otro
- [x] Descarga del acta de cada OT desde el historial
- [x] El hospital ve el historial de sus equipos

**Implementación:**
Historial por equipo con próximos mantenimientos y cumplimiento en el portal (fa7c469); historial con tipo y filtro, también en el portal (ba517d2). Endpoint en backend/apps/assets/views.py y descarga del acta en AssetDetailPage.jsx.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `trazabilidad`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
