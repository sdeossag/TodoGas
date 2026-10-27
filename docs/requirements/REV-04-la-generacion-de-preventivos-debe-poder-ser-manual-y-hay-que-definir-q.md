---
id: REV-04
issue: 99
titulo: "La generación de preventivos debe poder ser manual, y hay que definir qué pasa con las no ejecutadas"
tipo: functional
prioridad: must-have
modulo: planes-pm
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: planes-pm']
---

# REV-04 - La generación de preventivos debe poder ser manual, y hay que definir qué pasa con las no ejecutadas

### REV-04: La generación de preventivos debe poder ser manual, y hay que definir qué pasa con las no ejecutadas
**Prioridad:** M

**Descripción:**
El cliente no quiere que el preventivo se genere siempre solo, porque a veces no se puede cumplir el mes programado. Se necesita generación manual y una regla clara para las OT no ejecutadas, sin acumular OT abiertas indefinidamente.

**Criterios de aceptación:**
- [x] La generación puede ser manual desde las tareas pendientes
- [x] Las tareas no ejecutadas se pueden reprogramar con causa
- [x] No se acumulan OT abiertas: la tarea pendiente es única por tarea y activo
- [ ] Elegir manual o automático por protocolo (hoy es un ajuste global)

**Implementación:**
El motor mantiene una tarea pendiente por tarea de protocolo y activo; la creación de OT es manual por defecto desde la pantalla de pendientes y existe reprogramación con causa (TaskReschedule). Archivos: backend/apps/maintenance/engine.py, models.py (c7e3046, 804f2c5).

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `planes-pm`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
