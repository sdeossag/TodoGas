---
id: RF-PM-05
issue: 126
titulo: "Catálogo configurable de tipos de tarea"
tipo: functional
prioridad: should-have
modulo: planes-pm
estado: CLOSED
etiquetas: ['priority: should-have', 'type: functional', 'mod: planes-pm', 'platform: backend', 'platform: web']
---

# RF-PM-05 - Catálogo configurable de tipos de tarea

### RF-PM-05: Catálogo configurable de tipos de tarea
**Prioridad:** S

**Descripción:**
Las tareas tienen distintos tipos y cada cliente puede usar los suyos. Un catálogo editable permite definirlos y decidir si cada uno cuenta como preventivo, correctivo u otro en los reportes.

**Criterios de aceptación:**
- [x] Existe un catálogo de tipos de tarea editable por el administrador
- [x] Se sembró con los tipos habituales de la herramienta que se usaba antes
- [x] Cada tipo indica si cuenta como preventivo, correctivo u otro
- [x] Una OT manual puede usar cualquier tipo del catálogo
- [x] Los reportes y el historial respetan esa clasificación

**Implementación:**
Implementado en `308967d`. Archivos clave: `backend/apps/maintenance/models.py`, `backend/apps/maintenance/serializers.py`, migraciones `0006_catalogo_tipos_de_tarea.py` y `0007_sembrar_tipos_de_tarea.py`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `planes-pm`
- Prioridad: `S`
- Fuente: `Revisión con el cliente (2026-09-10)`
