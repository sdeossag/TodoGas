---
id: RF-MI-04
issue: 55
titulo: "Validación y rollback de la migración"
tipo: functional
prioridad: must-have
modulo: migracion
estado: OPEN
etiquetas: ['priority: must-have', 'type: functional', 'mod: migracion']
---

# RF-MI-04 - Validación y rollback de la migración

### RF-MI-04: Validación y rollback de la migración
**Prioridad:** M

**Descripción:**
El proceso de migración es validable y reversible antes de la puesta en producción definitiva.

**Criterios de aceptación:**
- La migración se ejecuta primero en el entorno de staging (no en producción) para validación completa.
- El `ADMIN` revisa los reportes de migración y puede solicitar correcciones al script antes de ejecutarlo en producción.
- Existe un proceso de rollback completo que permite eliminar todos los datos migrados de una ejecución específica para repetir el proceso corregido (solo disponible en staging; en producción el rollback requiere restaurar un backup).
- El plan de migración incluye una ventana de tiempo definida (fecha/hora) con el equipo de la empresa para ejecutar la migración a producción con mínima interrupción del servicio.

---

## MÓDULO NT — Notificaciones y Comunicaciones
