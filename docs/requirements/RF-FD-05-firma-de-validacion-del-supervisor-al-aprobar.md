---
id: RF-FD-05
issue: 133
titulo: "Firma de validación del supervisor al aprobar"
tipo: functional
prioridad: must-have
modulo: firma-digital, pdf
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: firma-digital', 'mod: pdf', 'platform: backend', 'platform: web']
---

# RF-FD-05 - Firma de validación del supervisor al aprobar

### RF-FD-05: Firma de validación del supervisor al aprobar
**Prioridad:** M

**Descripción:**
Al aprobar una orden, el supervisor firma como validación y el acta muestra quién validó, cuándo y quién ejecutó el trabajo, con horas reales.

**Criterios de aceptación:**
- [x] Al aprobar se usa la firma del supervisor
- [x] El acta muestra «Validado por» con fecha y hora
- [x] El acta muestra el ejecutor y la hora real del trabajo
- [x] La validación se guarda con la OT
- [x] Sin firma guardada la aprobación lo indica

**Implementación:**
Implementado en `1ba2e09` (hora real, ejecutor y validación) y `2721e08`. Archivos clave: `backend/apps/checklists/views.py`, `backend/apps/evidence/serializers.py`, `backend/apps/reports/generator.py`, `backend/apps/reports/tasks.py`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `firma-digital, pdf`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-10-23)`
