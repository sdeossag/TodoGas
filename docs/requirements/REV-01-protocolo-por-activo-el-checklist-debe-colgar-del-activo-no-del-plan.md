---
id: REV-01
issue: 96
titulo: "Protocolo por activo: el checklist debe colgar del activo, no del plan"
tipo: functional
prioridad: must-have
modulo: planes-pm
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: planes-pm']
---

# REV-01 - Protocolo por activo: el checklist debe colgar del activo, no del plan

### REV-01: Protocolo por activo: el checklist debe colgar del activo, no del plan
**Prioridad:** M

**Descripción:**
El modelo anterior ataba un solo checklist al plan compartido por todos los activos. En la revisión se pidió que el protocolo se asigne al activo una sola vez y que equipos distintos puedan tener protocolos distintos sin tocar los demás. También se pidió usar el término «protocolo» en la interfaz.

**Criterios de aceptación:**
- [x] Un activo se asocia a su propio protocolo y este no se vuelve a tocar
- [x] Cambiar el checklist de un activo no afecta a los demás
- [x] Al generar OT cada activo arrastra su propio checklist
- [x] La interfaz usa el término «protocolo»

**Implementación:**
Los planes pasaron a ser protocolos con tareas (PlanTask), cada una con su checklist; las tareas pendientes se crean por tarea y activo (c7e3046). El activo guarda una checklist predeterminada y la fecha de inicio al asignar (73486d1). Renombrado a «protocolos» en la interfaz (66a241d). Archivos: backend/apps/maintenance/models.py, backend/apps/assets/models.py.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `planes-pm`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
