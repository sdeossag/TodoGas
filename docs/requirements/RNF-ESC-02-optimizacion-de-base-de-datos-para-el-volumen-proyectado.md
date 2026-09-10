---
id: RNF-ESC-02
issue: 73
titulo: "Optimización de base de datos para el volumen proyectado"
tipo: non-functional
prioridad: must-have
modulo: escalabilidad
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: escalabilidad']
---

# RNF-ESC-02 - Optimización de base de datos para el volumen proyectado

### RNF-ESC-02: Optimización de base de datos para el volumen proyectado
**Prioridad:** M

**Descripción:**
El esquema de base de datos tiene los índices y optimizaciones necesarias para operar eficientemente con el volumen actual y proyectado de datos.

**Criterios de aceptación:**
- Los campos usados frecuentemente en filtros y búsquedas tienen **índices de base de datos** definidos explícitamente en las migraciones de Django: `activo.codigo_interno`, `activo.hospital_id`, `activo.estado`, `ot.tecnico_id`, `ot.estado`, `ot.hospital_id`, `ot.fecha_limite`, `log_auditoria.usuario_id`, `log_auditoria.timestamp`, `log_auditoria.entidad_tipo`.
- La búsqueda por texto libre en activos usa **PostgreSQL Full-Text Search** (GIN index en campos `nombre`, `modelo`, `numero_serie`) en lugar de LIKE con comodín al inicio.
- Las consultas de listados paginados usan **cursor-based pagination** o **keyset pagination** (no offset pagination) para tablas con más de 10,000 registros (específicamente el log de auditoría), evitando degradación de performance a medida que crecen los datos.
- Se ejecuta **EXPLAIN ANALYZE** en todas las queries críticas (listados, búsquedas, dashboards de KPIs) durante el desarrollo y se documenta el plan de ejecución. Ninguna query crítica tiene un Seq Scan en tablas con más de 1,000 registros.
- Las tareas de mantenimiento de la base de datos (VACUUM, ANALYZE) se delegan a RDS (mantenimiento automático de AWS) y están configuradas para ejecutarse en la ventana de mantenimiento fuera del horario operativo.

---

## RNF-USA — Usabilidad en Campo
