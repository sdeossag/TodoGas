---
id: RF-CK-06
issue: 121
titulo: "Respuesta Sí/No/N/A en el checklist"
tipo: functional
prioridad: should-have
modulo: checklists
estado: CLOSED
etiquetas: ['priority: should-have', 'type: functional', 'mod: checklists', 'platform: backend', 'platform: web']
---

# RF-CK-06 - Respuesta Sí/No/N/A en el checklist

### RF-CK-06: Respuesta Sí/No/N/A en el checklist
**Prioridad:** S

**Descripción:**
Hay pasos de revisión donde algunas veces la pregunta no aplica al equipo. El tipo Sí/No tiene una casilla «Permite N/A» para ofrecer esa tercera respuesta.

**Criterios de aceptación:**
- [x] El paso Sí/No tiene la casilla «Permite N/A», marcada por defecto
- [x] El técnico puede responder Sí, No o N/A cuando está permitido
- [x] La validación del checklist acepta N/A y no lo cuenta como respuesta faltante
- [x] El acta muestra solo la respuesta del paso
- [x] Los pasos ya existentes siguen funcionando

**Implementación:**
Implementado en `7bab9ba`. Archivos clave: `backend/apps/checklists/models.py`, `backend/apps/checklists/validators.py`, `backend/apps/reports/generator.py`, `frontend/src/components/checklists/ChecklistPreview.jsx`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `checklists`
- Prioridad: `S`
- Fuente: `Revisión con el cliente (2026-09-10)`
