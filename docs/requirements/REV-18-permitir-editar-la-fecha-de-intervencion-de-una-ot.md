---
id: REV-18
issue: 114
titulo: "Permitir editar la fecha de intervención de una OT"
tipo: functional
prioridad: could-have
modulo: ordenes-trabajo
estado: CLOSED
etiquetas: ['priority: could-have', 'type: functional', 'mod: ordenes-trabajo']
---

# REV-18 - Permitir editar la fecha de intervención de una OT

### REV-18: Permitir editar la fecha de intervención de una OT
**Prioridad:** C

**Descripción:**
La fecha de intervención quedaba fija con la ejecución real y se preguntó si podía corregirse. Hay que decidir quién puede hacerlo sin romper la trazabilidad ni la inalterabilidad de las OT cerradas.

**Criterios de aceptación:**
- [x] Se puede corregir la fecha de intervención en revisión
- [x] Lo calculado no se pisa; el acta usa la corrección si existe
- [x] Cubierto por pruebas y por el hash de integridad

**Implementación:**
Campos intervention_start_override e intervention_end_override (5ed8863), usados por el acta y por la integridad. Archivos: backend/apps/work_orders/models.py, backend/apps/reports/generator.py.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `ordenes-trabajo`
- Prioridad: `C`
- Fuente: `Revisión con el cliente (2026-09-10)`
