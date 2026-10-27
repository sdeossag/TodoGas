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

---

---

**Metadatos de importacion**
- Tipo: `Requisito no funcional`
- Fase: `2`
- Repositorio destino: `sdeossag/TodoGas`
- Categoria: `BAK - Respaldo y Retención de Datos`
- Prioridad: `M`
- Fuente: `CMMS Gases Medicinales - Fase 2: Requisitos No Funcionales`

**Implementación (revisión del 2026-10-27):**
- [x] Backups diarios con retención de 30 días — backup_retention_dias=30 por defecto
- [x] PITR habilitado — Se activa con la retención de backups
- [x] Ventana de backup de madrugada, fuera de horario — 07:00-08:00 UTC (02:00 Colombia); el requisito dice 02:00-04:00 UTC
- [ ] pg_dump semanal en un bucket separado por 90 días — No hay tarea ni bucket
- [ ] Restauración documentada y probada en staging — No hay documento ni prueba

Commits: 45090aa
Archivos: `infra/terraform/rds.tf`, `infra/terraform/prod.tfvars`, `infra/terraform/staging.tfvars`
