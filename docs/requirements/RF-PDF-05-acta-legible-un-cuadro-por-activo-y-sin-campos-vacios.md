---
id: RF-PDF-05
issue: 136
titulo: "Acta legible: un cuadro por activo y sin campos vacíos"
tipo: functional
prioridad: must-have
modulo: pdf
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: pdf', 'platform: backend']
---

# RF-PDF-05 - Acta legible: un cuadro por activo y sin campos vacíos

### RF-PDF-05: Acta legible: un cuadro por activo y sin campos vacíos
**Prioridad:** M

**Descripción:**
El acta era larga y difícil de leer. Ahora cada activo tiene su cuadro, se omiten campos vacíos y el título cabe en una línea.

**Criterios de aceptación:**
- [x] Un cuadro por activo
- [x] No se muestran campos vacíos
- [x] Sin hora en el campo «Emitido» ni estado
- [x] El logo queda separado del título
- [x] «ACTA DE SERVICIO» en una sola línea

**Implementación:**
Implementado en `6e45d14` (diseño del acta) y `89e12d6` (logo y título). Archivos clave: `backend/apps/reports/generator.py`, `backend/apps/reports/options.py`, `backend/apps/reports/templates/reports/service_report.html`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `pdf`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-10-23)`
