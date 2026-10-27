---
id: REV-22
issue: 117
titulo: "`restrict_to_hospital` de los planes PM no se aplica en ningún sitio"
tipo: bug
prioridad: should-have
modulo: planes-pm
estado: CLOSED
etiquetas: ['priority: should-have', 'type: bug', 'mod: planes-pm']
---

# REV-22 - `restrict_to_hospital` de los planes PM no se aplica en ningún sitio

### REV-22: El campo restrict_to_hospital de los planes PM no se aplica en ningún sitio
**Prioridad:** S

**Descripción:**
El campo restrict_to_hospital se guardaba y mostraba pero nunca validaba ni filtraba, por lo que un plan restringido a un hospital aceptaba activos de otro. Se debía aplicarlo de verdad o retirarlo.

**Criterios de aceptación:**
- [x] Se valida al añadir activos al protocolo
- [x] Se valida al asignar el protocolo desde el activo

**Implementación:**
Validaciones en backend/apps/maintenance/views.py y backend/apps/assets/serializers.py (c7e3046, 5fd3e08).

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `planes-pm`
- Prioridad: `S`
- Fuente: `Barrido QA (2026-09-08)`
