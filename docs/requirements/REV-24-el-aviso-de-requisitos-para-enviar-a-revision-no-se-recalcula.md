---
id: REV-24
issue: 119
titulo: "El aviso de requisitos para enviar a revisión no se recalcula"
tipo: bug
prioridad: could-have
modulo: ordenes-trabajo
estado: CLOSED
etiquetas: ['priority: could-have', 'type: bug', 'mod: ordenes-trabajo']
---

# REV-24 - El aviso de requisitos para enviar a revisión no se recalcula

### REV-24: El aviso de requisitos para enviar a revisión no se recalcula
**Prioridad:** C

**Descripción:**
Tras completar el checklist y subir la foto, el aviso de lo que falta seguía visible hasta recargar la página. Había que invalidar el estado de la OT cuando cambian checklist o evidencia.

**Criterios de aceptación:**
- [x] El aviso se recalcula al cambiar el checklist
- [x] El aviso se recalcula al subir fotos o firmas
- [x] Funciona sin red contando lo pendiente en el teléfono

**Implementación:**
Hook useReviewRequirements con consultas de fotos y firmas invalidadas al subir (frontend/src/api/evidence.js) y checklists que invalidan work-orders (frontend/src/api/checklists.js); funcionamiento sin red en b065c1d.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `ordenes-trabajo`
- Prioridad: `C`
- Fuente: `Barrido QA (2026-09-08)`
