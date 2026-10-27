---
id: RF-PM-06
issue: 127
titulo: "Protocolo asignable a una ubicación"
tipo: functional
prioridad: must-have
modulo: planes-pm
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: planes-pm', 'platform: backend', 'platform: web']
---

# RF-PM-06 - Protocolo asignable a una ubicación

### RF-PM-06: Protocolo asignable a una ubicación
**Prioridad:** M

**Descripción:**
Hay mantenimientos que se piensan por lugar y no equipo por equipo. Se puede asignar un protocolo a una ubicación del árbol y se aplica a los equipos que están en ella.

**Criterios de aceptación:**
- [x] Se puede asignar un protocolo a una ubicación
- [x] La asignación alcanza a los equipos de esa ubicación y sus ramas
- [x] Los equipos nuevos o movidos se reflejan en la asignación
- [x] La OT y el acta muestran la ubicación
- [x] Existen datos de demostración para probarlo

**Implementación:**
Implementado en `5ed8863`. Archivos clave: `backend/apps/assets/activo_ubicacion.py`, `backend/apps/maintenance/services.py`, `backend/apps/assets/management/commands/seed_demo.py`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `planes-pm`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
