---
id: REV-19
issue: 106
titulo: "El administrador debe poder corregir checklist y evidencia mientras la OT está en revisión"
tipo: functional
prioridad: should-have
modulo: ordenes-trabajo
estado: CLOSED
etiquetas: ['priority: should-have', 'type: functional', 'mod: ordenes-trabajo']
---

# REV-19 - El administrador debe poder corregir checklist y evidencia mientras la OT está en revisión

### REV-19: El administrador debe poder corregir checklist y evidencia mientras la OT está en revisión
**Prioridad:** S

**Descripción:**
El administrador necesita modificar el checklist y la evidencia enviados mientras la OT está en revisión, sin perder la trazabilidad ni la inalterabilidad una vez finalizada.

**Criterios de aceptación:**
- [x] Editar respuestas del checklist en estado IN_REVIEW
- [x] Agregar, describir u ocultar fotos sin borrarlas
- [x] Queda quién corrigió y el valor anterior en auditoría
- [x] Tras finalizar, la OT sigue inalterable (hash de integridad)

**Implementación:**
Corrección en revisión con «Corregido por», valor anterior en auditoría y fotos ocultas del acta, con hash de integridad v5 (cdaa4f3). Archivos: backend/apps/checklists/views.py, backend/apps/evidence/views.py, backend/apps/work_orders/integrity.py.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `ordenes-trabajo`
- Prioridad: `S`
- Fuente: `Revisión con el cliente (2026-09-10)`
