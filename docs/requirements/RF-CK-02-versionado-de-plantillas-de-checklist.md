---
id: RF-CK-02
issue: 21
titulo: "Versionado de plantillas de checklist"
tipo: functional
prioridad: must-have
modulo: checklists
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: checklists']
---

# RF-CK-02 - Versionado de plantillas de checklist

### RF-CK-02: Versionado de plantillas de checklist
**Prioridad:** M

**Descripción:**
Las plantillas tienen control de versiones automático para garantizar la trazabilidad regulatoria de qué versión exacta del checklist fue aplicada en cada OT.

**Criterios de aceptación:**
- Cada vez que el ADMIN edita y guarda una plantilla de checklist, el sistema crea automáticamente una nueva versión (v1, v2, v3...) y archiva la anterior.
- Las OTs ya completadas mantienen referencia inmutable a la versión del checklist con la que fueron ejecutadas. Al consultar una OT completada, se muestra exactamente el checklist en la versión que se usó (incluyendo opciones que puedan haber sido eliminadas en versiones posteriores).
- Las OTs futuras creadas desde planes o manualmente usan siempre la versión más reciente activa de la plantilla.
- El ADMIN puede ver el historial de versiones de una plantilla: fecha de cada versión, usuario que la modificó, descripción del cambio (campo opcional al guardar una nueva versión).
- No se puede eliminar una versión de checklist que haya sido usada en al menos una OT.
