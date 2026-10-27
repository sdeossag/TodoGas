---
id: REV-14
issue: 110
titulo: "Comprimir las fotos preservando calidad suficiente para auditoría"
tipo: functional
prioridad: must-have
modulo: evidencia
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: evidencia']
---

# REV-14 - Comprimir las fotos preservando calidad suficiente para auditoría

### REV-14: Comprimir las fotos preservando calidad suficiente para auditoría
**Prioridad:** M

**Descripción:**
Existe un límite de tamaño que impide subir fotos grandes, pero los equipos auditados exigen fotos que se vean bien. Se acordó comprimir de forma transparente al guardar, preservando calidad suficiente.

**Criterios de aceptación:**
- [x] La foto se comprime al guardar sin intervención del técnico
- [x] Solo se reduce lo que excede el límite
- [ ] Umbral de calidad mínimo documentado y validado con el cliente

**Implementación:**
Compresión en el teléfono para fotos que superan el límite (0a360e0) y envío a revisión sin bloqueos con muchas fotos (b065c1d). Archivos: frontend/src/utils/compressImage.js, photoSize.js.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `evidencia`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
