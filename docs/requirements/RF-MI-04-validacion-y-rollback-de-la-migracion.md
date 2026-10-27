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

---

---

**Metadatos de importacion**
- Repositorio destino: `sdeossag/TodoGas`
- Modulo: `MI - Migración de Datos desde Fracttal`
- Prioridad: `M`
- Fuente: `CMMS_Fase1_Requisitos_Funcionales.md`

**Implementación (revisión del 2026-10-27):**
- [x] Ejecutar primero en staging — Existe configuración de staging en infra (backend-staging.hcl) y el comando se puede correr allí; no hay procedimiento escrito.
- [x] El ADMIN revisa reportes antes de aplicar — Vista previa sin escribir; con errores no aplica nada.
- [ ] Rollback de una ejecución, solo en staging — Solo es atómico (todo o nada). No hay deshacer una ejecución ya aplicada; la auditoría guarda conteos, no los ids creados.
- [ ] Plan con ventana de tiempo para producción — No hay documento.

Commits: 8fcd0b1, 45090aa
Archivos: `backend/apps/assets/importacion_fracttal.py`, `infra/README.md`, `infra/terraform/backend-staging.hcl`
