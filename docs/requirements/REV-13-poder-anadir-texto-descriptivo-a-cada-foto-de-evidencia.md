---
id: REV-13
issue: 109
titulo: "Poder añadir texto descriptivo a cada foto de evidencia"
tipo: functional
prioridad: should-have
modulo: evidencia
estado: CLOSED
etiquetas: ['priority: should-have', 'type: functional', 'mod: evidencia']
---

# REV-13 - Poder añadir texto descriptivo a cada foto de evidencia

### REV-13: Poder añadir texto descriptivo a cada foto de evidencia
**Prioridad:** S

**Descripción:**
Se necesita poder agregar un texto a cada foto, por ejemplo «antes» o «después», que el técnico escriba al subirla y que aparezca junto a la imagen en el acta.

**Criterios de aceptación:**
- [x] Campo de descripción por foto al subirla
- [x] La descripción aparece junto a la foto en el acta
- [x] Se puede editar en revisión

**Implementación:**
Campo caption en la evidencia y captura con descripción (334d516); edición de la descripción en revisión (cdaa4f3). Archivos: backend/apps/evidence/models.py, PhotoCapture.jsx, service_report.html.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `evidencia`
- Prioridad: `S`
- Fuente: `Revisión con el cliente (2026-09-10)`
