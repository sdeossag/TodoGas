---
id: RF-MI-03
issue: 54
titulo: "Migración de historial de OTs"
tipo: functional
prioridad: must-have
modulo: migracion
estado: OPEN
etiquetas: ['priority: must-have', 'type: functional', 'mod: migracion', 'needs-fracttal-review']
---

# RF-MI-03 - Migración de historial de OTs

### RF-MI-03: Migración de historial de OTs
**Prioridad:** M

**Descripción:**
El historial de OTs anteriores de Fracttal se importa al nuevo sistema para preservar la trazabilidad completa de los activos desde el inicio de la operación.

**Criterios de aceptación:**
- Las OTs históricas de Fracttal se importan en estado "Completada" con una marca visual de "Migrado desde Fracttal" y la fecha original de la OT en Fracttal.
- Los campos de la OT de Fracttal que no existan en el nuevo sistema se consolidan en el campo "observaciones de migración" de la OT importada.
- Si los PDFs de las OTs históricas son exportables desde Fracttal: se almacenan en S3 vinculados a la OT migrada. Si no son exportables: se registra una nota de texto con la referencia a Fracttal ("Ver OT #{id_fracttal} en sistema anterior para PDF original").
- El historial migrado es inmutable desde el momento de la importación (mismas reglas que OTs del nuevo sistema).
- El reporte de migración incluye: OTs migradas exitosamente, OTs con errores, OTs sin activo mapeado (requieren asociación manual), PDFs migrados vs. no migrados.
- Dependencia: **la migración de OTs solo puede ejecutarse después de completar y validar la migración de activos** (RF-MI-02), ya que las OTs referencian activos.

> ⚠️ El alcance exacto de la migración de OTs depende de qué campos y formatos permite exportar Fracttal con rol administrador. Definir tras revisión del módulo de reportes/exportación de Fracttal.
