---
id: RNF-DIS-02
issue: 64
titulo: "Recuperación ante fallos (RTO y RPO)"
tipo: non-functional
prioridad: must-have
modulo: disponibilidad
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: disponibilidad']
---

# RNF-DIS-02 - Recuperación ante fallos (RTO y RPO)

### RNF-DIS-02: Recuperación ante fallos (RTO y RPO)
**Prioridad:** M

**Descripción:**
El sistema define objetivos claros de recuperación ante desastres o fallas mayores de infraestructura.

**Criterios de aceptación:**
- **RTO (Recovery Time Objective):** el sistema debe estar restaurado y operativo en máximo **4 horas** después de una falla mayor de infraestructura (ej: falla de instancia EC2/ECS, corrupción de base de datos).
- **RPO (Recovery Point Objective):** en el peor caso de pérdida de datos, el sistema no debe perder más de **24 horas** de datos (respaldados por backups diarios). Lo ideal es ≤ 1 hora gracias a Point-in-Time Recovery de RDS.
- La base de datos PostgreSQL se despliega en **AWS RDS con Multi-AZ** para failover automático ante falla de la instancia primaria (failover típico en ≤ 60 segundos, transparente para la aplicación).
- Las imágenes y PDFs almacenados en S3 tienen **versionado habilitado** para proteger contra eliminaciones accidentales.
- Se documenta y prueba el procedimiento de recuperación ante desastres **al menos una vez antes del lanzamiento a producción** (ejercicio de DR).
