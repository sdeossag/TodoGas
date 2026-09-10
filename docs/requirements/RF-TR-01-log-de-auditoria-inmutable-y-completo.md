---
id: RF-TR-01
issue: 32
titulo: "Log de auditoría inmutable y completo"
tipo: functional
prioridad: must-have
modulo: trazabilidad
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: trazabilidad']
---

# RF-TR-01 - Log de auditoría inmutable y completo

### RF-TR-01: Log de auditoría inmutable y completo
**Prioridad:** M

**Descripción:**
El sistema mantiene un log de auditoría completo e inmutable de todas las acciones relevantes realizadas en el sistema. Este log es el respaldo primario para auditorías de INVIMA, inspecciones de Buenas Prácticas de Manufactura (BPM/GMP), y resolución de disputas con clientes.

**Criterios de aceptación:**
- **Cada entrada del log registra sin excepción:** timestamp UTC con precisión de milisegundos, ID y nombre del usuario que realizó la acción, rol del usuario en el momento de la acción, tipo de acción (en texto legible en español), entidad afectada (tipo + ID + nombre si aplica), valores anteriores y nuevos (formato JSON para cambios de campos), IP del cliente para acciones web y device ID para acciones desde app, resultado de la acción (éxito / error con código).
- **Acciones auditadas:** login y logout; intentos de login fallidos; creación/edición/baja de activos; creación/edición/cancelación de OTs; cambios de estado de OTs; asignación/reasignación de técnicos; creación/edición de planes de mantenimiento; creación/edición de plantillas de checklist (con versión creada); captura y confirmación de firmas digitales; generación de PDFs; envíos de PDF a clientes; creación/edición/desactivación de usuarios; movimientos de inventario; descarga de documentos por el CLI; intentos de acceso no autorizado (403).
- El log **nunca puede ser modificado, eliminado ni ocultado** por ningún rol, incluyendo el `ADMIN`. No existe ningún endpoint ni interfaz para eliminar entradas del log.
- El log es consultable por el `ADMIN` con filtros por: usuario, tipo de acción, entidad, rango de fechas. Retorna resultados paginados.
- El sistema retiene el log por **mínimo 5 años** sin purga automática.
- En un escenario de auditoría, el `ADMIN` puede exportar el log filtrado a CSV.
