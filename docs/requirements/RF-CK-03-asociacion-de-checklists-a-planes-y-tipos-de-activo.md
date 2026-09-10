---
id: RF-CK-03
issue: 22
titulo: "Asociación de checklists a planes y tipos de activo"
tipo: functional
prioridad: must-have
modulo: checklists
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: checklists']
---

# RF-CK-03 - Asociación de checklists a planes y tipos de activo

### RF-CK-03: Asociación de checklists a planes y tipos de activo
**Prioridad:** M

**Descripción:**
Las plantillas de checklist se asocian a planes de mantenimiento y pueden definirse como checklist por defecto por tipo de activo para agilizar la creación de OTs correctivas.

**Criterios de aceptación:**
- Al crear o editar un plan de mantenimiento, el `ADMIN` selecciona obligatoriamente la plantilla de checklist que se usará en las OTs generadas por ese plan.
- Un tipo de activo puede tener configurado hasta 3 "checklists por defecto" según el tipo de intervención: uno para correctivo, uno para preventivo, uno para predictivo. Al crear una OT correctiva sobre ese activo, la plantilla correspondiente se preselecciona automáticamente (el ADMIN puede cambiarla antes de guardar).
- Al crear una OT sin checklist asociado, el ADMIN ve una advertencia visual clara. Puede proceder igualmente (la OT sin checklist solo requiere foto + firma del técnico para cerrarse).
- El ADMIN puede ver qué planes y OTs están usando actualmente cada plantilla de checklist (vista de uso).
