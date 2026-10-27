---
id: REV-08
issue: 103
titulo: "Las lecturas de medidor deben quedar asociadas al activo, no solo a la OT"
tipo: functional
prioridad: should-have
modulo: activos
estado: CLOSED
etiquetas: ['priority: should-have', 'type: functional', 'mod: activos']
---

# REV-08 - Las lecturas de medidor deben quedar asociadas al activo, no solo a la OT

### REV-08: Las lecturas de medidor deben quedar asociadas al activo, no solo a la OT
**Prioridad:** S

**Descripción:**
Una lectura de medidor vivía solo dentro de la respuesta del checklist y se perdía allí. Se necesita que voltajes, corrientes y horas queden como serie histórica del activo, consultable desde su ficha y capaz de activar protocolos por medidor.

**Criterios de aceptación:**
- [x] Las lecturas del checklist se propagan al medidor del activo
- [x] Se consultan desde la ficha del activo
- [x] Las tareas se pueden activar por uso o por umbral

**Implementación:**
Modelos Meter, MeterUnit y MeterReading, con lecturas desde el checklist y a mano, y activadores «Cada» y «Cuando» (2ab4339). Archivos: backend/apps/assets/models.py, backend/apps/maintenance/meters.py.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `activos`
- Prioridad: `S`
- Fuente: `Revisión con el cliente (2026-09-10)`
