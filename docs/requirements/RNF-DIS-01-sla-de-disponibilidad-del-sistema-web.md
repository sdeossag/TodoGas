---
id: RNF-DIS-01
issue: 63
titulo: "SLA de disponibilidad del sistema web"
tipo: non-functional
prioridad: must-have
modulo: disponibilidad
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: disponibilidad']
---

# RNF-DIS-01 - SLA de disponibilidad del sistema web

### RNF-DIS-01: SLA de disponibilidad del sistema web
**Prioridad:** M

**Descripción:**
El sistema web (API + frontend) debe estar disponible de forma continua para los usuarios, con una disponibilidad mínima definida y ventanas de mantenimiento planificadas.

**Criterios de aceptación:**
- **Disponibilidad mínima:** 99.5% mensual medido sobre el período 06:00 AM – 10:00 PM (hora Colombia, UTC-5). Esto equivale a máximo ~2.4 horas de interrupción no planificada al mes en horario de operación.
- **Fuera del horario de operación** (10:00 PM – 06:00 AM): se permiten ventanas de mantenimiento planificadas con aviso previo de 24 horas al ADMIN vía correo.
- El cálculo de disponibilidad excluye: interrupciones de menos de 2 minutos continuos, ventanas de mantenimiento notificadas con 24 horas de anticipación, e interrupciones causadas por el proveedor de internet del cliente (fuera del control del sistema).
- En caso de caída del sistema, el ADMIN y el equipo de desarrollo deben recibir una alerta automática vía correo y/o Slack dentro de los **3 minutos** de detectada la interrupción (monitoreo via AWS CloudWatch + alarmas).
- La app Android opera en modo offline durante caídas del servidor, sin interrupción para el técnico de campo (ver módulo OF en Fase 1).

---

---

**Metadatos de importacion**
- Tipo: `Requisito no funcional`
- Fase: `2`
- Repositorio destino: `sdeossag/TodoGas`
- Categoria: `DIS - Disponibilidad y Confiabilidad`
- Prioridad: `M`
- Fuente: `CMMS Gases Medicinales - Fase 2: Requisitos No Funcionales`

**Implementación (revisión del 2026-10-27):**
- [ ] Disponibilidad 99,5% en horario de operación — Solo se puede verificar en producción
- [ ] Alerta automática en 3 minutos tras una caída — Alarma de hosts sanos (3 periodos de 60 s) con aviso por SNS al correo; falta probarla en AWS
- [ ] Aviso de 24 h para mantenimiento planificado — Es un proceso y no está documentado
- [x] App Android sigue en modo offline durante caídas — SQLite local, cola de sincronización y banner offline

Commits: 45090aa
Archivos: `infra/terraform/monitoreo.tf`, `infra/terraform/alb.tf`, `frontend/src/db/database.js`
