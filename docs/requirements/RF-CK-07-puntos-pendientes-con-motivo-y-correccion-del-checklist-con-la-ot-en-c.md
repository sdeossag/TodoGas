---
id: RF-CK-07
issue: 122
titulo: "Puntos pendientes con motivo y corrección del checklist con la OT en curso"
tipo: functional
prioridad: must-have
modulo: checklists
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: checklists', 'platform: backend', 'platform: android']
---

# RF-CK-07 - Puntos pendientes con motivo y corrección del checklist con la OT en curso

### RF-CK-07: Puntos pendientes con motivo y corrección del checklist con la OT en curso
**Prioridad:** M

**Descripción:**
En campo a veces no se alcanza a revisar un punto. El técnico puede dejarlo como pendiente indicando el motivo, y puede reabrir y corregir el checklist mientras la orden de trabajo sigue en curso.

**Criterios de aceptación:**
- [x] El técnico puede marcar un punto como pendiente y debe escribir el motivo
- [x] Los pendientes y su motivo quedan guardados y visibles en la orden
- [x] El checklist cerrado se puede corregir mientras la OT está en curso
- [x] Los cambios se sincronizan desde la app
- [x] Una vez enviada a revisión ya no se corrige como técnico

**Implementación:**
Implementado en `2721e08` (junto con la firma de validación). Archivos clave: `backend/apps/checklists/models.py`, `backend/apps/checklists/serializers.py`, `backend/apps/checklists/views.py`, migración `0010_pendientes_del_checklist.py`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `checklists`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-10-23)`
