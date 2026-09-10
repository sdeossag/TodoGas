---
id: RNF-BAK-01
issue: 89
titulo: "Política de backups de la base de datos"
tipo: non-functional
prioridad: must-have
modulo: backup-retencion
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: backup-retencion']
---

# RNF-BAK-01 - Política de backups de la base de datos

### RNF-BAK-01: Política de backups de la base de datos
**Prioridad:** M

**Descripción:**
La base de datos PostgreSQL tiene backups automáticos frecuentes con retención suficiente para cubrir los escenarios de pérdida de datos más probables.

**Criterios de aceptación:**
- **AWS RDS Automated Backups:** backups automáticos diarios del snapshot completo de la instancia RDS. Retención de **30 días** (ventana de 30 días para restaurar a cualquier punto).
- **Point-in-Time Recovery (PITR):** habilitado en RDS, permite restaurar la base de datos a cualquier segundo dentro de los últimos 30 días. Esto da un RPO efectivo de segundos, no horas.
- Los snapshots automáticos se realizan durante la ventana de mantenimiento configurada (02:00 AM – 04:00 AM UTC, fuera del horario de operación en Colombia).
- Adicionalmente a los backups de RDS, se realiza un **dump de PostgreSQL** (`pg_dump`) semanal y se almacena en un bucket S3 **separado** de la infraestructura principal (protección contra eliminación accidental del bucket principal o errores de configuración de RDS). El dump semanal se retiene por **90 días**.
- El procedimiento de restauración desde backup está **documentado y probado** antes del lanzamiento a producción. La restauración de un backup de 30 días atrás se prueba al menos una vez en staging.
