---
id: RF-CK-05
issue: 120
titulo: "Bloques repetibles en el checklist"
tipo: functional
prioridad: must-have
modulo: checklists
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: checklists', 'platform: backend', 'platform: web', 'platform: android']
---

# RF-CK-05 - Bloques repetibles en el checklist

### RF-CK-05: Bloques repetibles en el checklist
**Prioridad:** M

**Descripción:**
Algunos equipos llevan varios elementos iguales (por ejemplo varias tomas o válvulas) que se revisan con las mismas preguntas. El checklist permite definir un bloque que se repite y su cantidad en el plan; en campo el técnico puede ajustarla con un aviso.

**Criterios de aceptación:**
- [x] El administrador puede marcar un grupo de pasos como bloque repetible con una cantidad inicial
- [x] La cantidad se define en el plan de mantenimiento
- [x] El técnico puede ajustar la cantidad en campo y la app muestra un aviso del cambio
- [x] El acta muestra cada repetición del bloque en una tabla
- [x] Funciona también sin red en la app del teléfono

**Implementación:**
Quedó en dos cortes: corte A (backend: modelo, migraciones, serializadores y vistas, `05a7998`) y corte B (web y teléfono, `36bcfd9`). Archivos clave: `backend/apps/checklists/models.py`, `backend/apps/reports/generator.py`, `frontend/src/components/checklists/ChecklistPreview.jsx`, `frontend/src/db/repositories.js`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `checklists`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
