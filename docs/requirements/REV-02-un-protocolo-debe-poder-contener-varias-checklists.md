---
id: REV-02
issue: 97
titulo: "Un protocolo debe poder contener varias checklists"
tipo: functional
prioridad: must-have
modulo: checklists
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: checklists']
---

# REV-02 - Un protocolo debe poder contener varias checklists

### REV-02: Un protocolo debe poder contener varias checklists
**Prioridad:** M

**Descripción:**
Un plan admitía un solo checklist, pero el cliente usa varios para un mismo protocolo: preventivo recurrente, pruebas de instalación de un solo uso y tareas por evento. Se necesita asociar varios checklists a un protocolo y que la OT sepa cuál aplica según el tipo de intervención.

**Criterios de aceptación:**
- [x] Un protocolo admite N tareas, cada una con su checklist
- [x] Hay tareas de un solo uso (repeat_count) y recurrentes
- [x] Cada tarea tiene un tipo de intervención del catálogo

**Implementación:**
PlanTask permite varias tareas por protocolo con checklist, frecuencia, número de repeticiones y tipo (c7e3046). El catálogo de tipos de tarea cuenta cada tipo como preventivo, correctivo u otro (308967d). Archivos: backend/apps/maintenance/models.py, backend/apps/maintenance/task_types.py.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `checklists`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
