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
