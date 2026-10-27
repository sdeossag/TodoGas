---
id: RF-PM-07
issue: 128
titulo: "Fecha de inicio al asignar un protocolo"
tipo: functional
prioridad: must-have
modulo: planes-pm
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: planes-pm', 'platform: backend', 'platform: web']
---

# RF-PM-07 - Fecha de inicio al asignar un protocolo

### RF-PM-07: Fecha de inicio al asignar un protocolo
**Prioridad:** M

**Descripción:**
Al asignar un protocolo hay que decir desde cuándo empieza a contar, para no generar tareas atrasadas. También se puede dejar un checklist predeterminado por equipo.

**Criterios de aceptación:**
- [x] Al asignar se pide la fecha de inicio
- [x] Las tareas se programan a partir de esa fecha
- [x] El equipo puede tener un checklist predeterminado
- [x] Se registran modelo y serie en el primer paso
- [x] La fecha queda guardada en la asignación

**Implementación:**
Implementado en `73486d1`. Archivos clave: `backend/apps/maintenance/services.py`, `backend/apps/maintenance/serializers.py`, `backend/apps/assets/models.py`, migración `0011_checklist_predeterminado_del_activo.py`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `planes-pm`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-10-23)`
