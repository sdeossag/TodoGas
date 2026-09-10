---
id: RF-AC-03
issue: 3
titulo: "Creación, edición y baja de activos"
tipo: functional
prioridad: must-have
modulo: activos
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: activos']
---

# RF-AC-03 - Creación, edición y baja de activos

### RF-AC-03: Creación, edición y baja de activos
**Prioridad:** M

**Descripción:**
El `ADMIN` gestiona completamente el ciclo de vida de los activos. El `SUP` puede editar datos técnicos pero no dar de baja activos. Los `TEC` y `CLI` no tienen permisos de escritura sobre activos.

**Criterios de aceptación:**
- Solo `ADMIN` puede crear nuevos activos y asignarlos a un hospital (nodo de la jerarquía).
- Solo `ADMIN` puede cambiar el estado de un activo a "Dado de baja".
- Al intentar dar de baja un activo con OTs activas (Pendiente / En Progreso / En Revisión), el sistema muestra una advertencia con el listado de OTs afectadas y requiere confirmación explícita. Las OTs abiertas deben resolverse antes de confirmar la baja, o el ADMIN puede forzar la baja documentando la razón.
- Un activo dado de baja no puede recibir nuevas OTs. Su historial, ficha técnica y reportes siguen siendo accesibles.
- No existe eliminación física de activos; únicamente baja lógica (soft delete).
- Cada edición de la ficha técnica queda registrada automáticamente en el log de trazabilidad con: usuario, fecha/hora, campo modificado, valor anterior, valor nuevo.
- El `SUP` puede editar campos de la ficha técnica pero no puede cambiar el estado del activo ni darlo de baja.
