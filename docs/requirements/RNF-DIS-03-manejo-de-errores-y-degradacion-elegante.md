---
id: RNF-DIS-03
issue: 65
titulo: "Manejo de errores y degradación elegante"
tipo: non-functional
prioridad: must-have
modulo: disponibilidad
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: disponibilidad']
---

# RNF-DIS-03 - Manejo de errores y degradación elegante

### RNF-DIS-03: Manejo de errores y degradación elegante
**Prioridad:** M

**Descripción:**
El sistema maneja los errores de forma que el usuario siempre recibe retroalimentación clara, y que una falla en un componente no derrumbe el sistema completo.

**Criterios de aceptación:**
- Ningún error interno del servidor (5xx) es visible al usuario final; en su lugar se muestra un mensaje amigable en español: "Ocurrió un error inesperado. El equipo técnico ha sido notificado. Por favor intenta nuevamente en unos minutos."
- Los errores 5xx se registran automáticamente en el sistema de monitoreo de errores (ej: **Sentry** o AWS CloudWatch Logs) con: stack trace completo, usuario que lo generó, endpoint, parámetros de la petición (sin datos sensibles).
- Si el servicio de generación de PDFs (Celery worker) falla, la OT igual queda marcada como "Completada" y se registra el fallo del PDF. El ADMIN recibe alerta y puede regenerar el PDF manualmente.
- Si el servicio de envío de correos (SMTP) falla, el sistema reintenta con backoff y notifica al ADMIN del fallo definitivo (ver RF-PDF-02). El fallo en el envío de correo no afecta el estado de la OT.
- Las tareas asíncronas de Celery tienen configurado un **tiempo máximo de ejecución** (timeout) y un número máximo de reintentos para evitar que workers queden bloqueados indefinidamente.
- La app Android muestra mensajes de error descriptivos cuando la sincronización falla, con la opción de "Reintentar" y la certeza de que los datos locales están seguros.

---

## RNF-SEG — Seguridad

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
- [ ] Sin 5xx visibles y mensaje amigable en español — No hay manejador global ni pantalla de error; no se encontró el texto pedido
- [x] Errores 5xx a Sentry o CloudWatch sin datos sensibles — Sentry con send_default_pii=False y logs a CloudWatch
- [x] Si falla el PDF la OT queda completada y el ADMIN ve el fallo — Registro del fallo en auditoría (failures.py) y regeneración manual
- [x] Reintentos con espera creciente en tareas de correo — max_retries=3 con espera creciente
- [ ] Tiempo máximo de ejecución en tareas Celery — No hay time_limit ni soft_time_limit
- [x] App Android: error de sincronización con Reintentar — SyncAttentionNotice con Reintentar

Commits: 45090aa, f57ddb2
Archivos: `backend/apps/reports/tasks.py`, `backend/apps/reports/failures.py`, `frontend/src/components/ui/SyncAttentionNotice.jsx`
