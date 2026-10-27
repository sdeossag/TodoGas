---
id: RF-OT-08
issue: 15
titulo: "OT generada automáticamente desde plan preventivo"
tipo: functional
prioridad: must-have
modulo: ordenes-trabajo
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: ordenes-trabajo']
---

# RF-OT-08 - OT generada automáticamente desde plan preventivo

### RF-OT-08: OT generada automáticamente desde plan preventivo
**Prioridad:** M

**Descripción:**
Las OTs preventivas se generan automáticamente por el sistema según la periodicidad de los planes de mantenimiento, sin intervención manual del ADMIN.

**Criterios de aceptación:**
- La generación automática corre como tarea Celery programada al inicio de cada día a las 06:00 AM (hora Colombia, UTC-5).
- Cada OT generada incluye automáticamente: referencia al plan que la originó, activo correspondiente, checklist preconfigurado en el plan, técnico preconfigurado en el plan (si existe), fecha límite calculada según la periodicidad del plan más el buffer configurado.
- Si el plan no tiene técnico preconfigurado, la OT se crea sin técnico asignado y el `ADMIN` recibe alerta inmediata.
- **Protección anti-duplicados:** si ya existe una OT activa (Pendiente / En Progreso / En Revisión) generada desde el mismo plan para el mismo activo, el sistema NO genera una nueva. En cambio, envía una alerta al ADMIN indicando que hay una OT pendiente de ese plan sin completar.
- Las OTs generadas automáticamente tienen un ícono diferenciador en el listado para distinguirlas de las creadas manualmente.
- El sistema registra en el log: fecha/hora de generación, plan origen, activo, resultado (generada / omitida por duplicado con referencia).

---

## MÓDULO PM — Planes de Mantenimiento Preventivo

---

---

**Metadatos de importacion**
- Repositorio destino: `sdeossag/TodoGas`
- Modulo: `OT - Órdenes de Trabajo`
- Prioridad: `M`
- Fuente: `CMMS_Fase1_Requisitos_Funcionales.md`

**Implementación (revisión del 2026-10-27):**
- [x] Tarea Celery diaria a las 06:00 Colombia — config/celery.py: crontab 11:00 UTC, maintenance.generate_preventive_work_orders. Repone las tareas pendientes.
- [ ] ~~Crear OT sola con plan, activo, checklist, técnico y fecha límite~~ (ya no aplica: Decisión del cliente: las OT preventivas no se crean solas; el planificador agrupa las tareas pendientes en OT. La creación automática existe pero está apagada (MAINTENANCE_AUTO_CREATE_WORK_ORDERS=False).)
- [ ] ~~Alerta al ADMIN si no hay técnico~~ (ya no aplica: La OT se asigna al armarla, no al generarse.)
- [x] Anti-duplicados con alerta al ADMIN — Una tarea con OT activa se omite y se avisa (engine.py); a nivel de tarea, no de plan.
- [ ] ~~Ícono para OT automáticas~~ (ya no aplica: No hay OT automáticas en el flujo actual.)
- [x] Log de generación — MaintenancePlanExecution y AuditLog por corrida.

Commits: c7e3046, 804f2c5
Archivos: `backend/apps/maintenance/engine.py`, `backend/config/celery.py`, `backend/apps/maintenance/tasks.py`
