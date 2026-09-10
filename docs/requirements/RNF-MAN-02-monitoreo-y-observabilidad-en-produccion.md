---
id: RNF-MAN-02
issue: 93
titulo: "Monitoreo y observabilidad en producción"
tipo: non-functional
prioridad: must-have
modulo: mantenibilidad
estado: CLOSED
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: mantenibilidad']
---

# RNF-MAN-02 - Monitoreo y observabilidad en producción

### RNF-MAN-02: Monitoreo y observabilidad en producción
**Prioridad:** M

**Descripción:**
El sistema en producción tiene suficiente visibilidad para detectar, diagnosticar, y resolver incidentes rápidamente.

**Criterios de aceptación:**
- **Monitoreo de infraestructura:** AWS CloudWatch con alarmas configuradas para: uso de CPU de la instancia EC2/ECS > 80% por más de 5 minutos, uso de memoria > 85%, espacio en disco > 80%, latencia de RDS P95 > 500 ms, profundidad de la cola de Celery > 50 tareas.
- **Monitoreo de errores de aplicación:** **Sentry** (u equivalente gratuito para el volumen del proyecto) integrado en el backend Django y en el frontend React. Captura automáticamente excepciones no manejadas con stack trace, contexto del request, y usuario (sin datos sensibles).
- **Logs de aplicación:** los logs de Django (nivel WARNING y ERROR en producción) se envían a **AWS CloudWatch Logs**. Los logs incluyen: nivel, timestamp, mensaje, request ID. Los logs de acceso del servidor web (Gunicorn/Nginx) se retienen por 30 días.
- **Health check endpoint:** el API expone `/health/` que retorna HTTP 200 con el estado de los servicios críticos (DB, Redis, S3 accesible). Este endpoint es consultado por el ALB para determinar si una instancia está sana.
- **Dashboard de operaciones:** CloudWatch dashboard con las métricas clave del sistema en una sola vista, accesible para el equipo de desarrollo.
- Las alertas de CloudWatch envían notificaciones al equipo de desarrollo vía correo electrónico y/o Slack (canal `#cmms-alerts`).
