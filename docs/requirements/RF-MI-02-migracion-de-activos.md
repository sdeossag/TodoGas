---
id: RF-MI-02
issue: 53
titulo: "Migración de activos"
tipo: functional
prioridad: must-have
modulo: migracion
estado: OPEN
etiquetas: ['priority: must-have', 'type: functional', 'mod: migracion', 'needs-fracttal-review']
---

# RF-MI-02 - Migración de activos

### RF-MI-02: Migración de activos
**Prioridad:** M

**Descripción:**
Los ~3,940 activos existentes en Fracttal se importan al nuevo sistema preservando toda la información disponible y respetando la jerarquía de activos.

**Criterios de aceptación:**
- El script procesa la exportación de activos de Fracttal (formato a definir con revisión del módulo de exportación de Fracttal).
- Se preserva la jerarquía de activos tal como está en Fracttal, mapeando a los niveles del nuevo sistema. Si hay diferencias de niveles jerárquicos, el script documenta el mapeo aplicado y el `ADMIN` lo valida.
- Los campos de Fracttal sin equivalente en el nuevo sistema se almacenan en los campos personalizados del activo o en un campo de "notas de migración" para revisión posterior.
- Cada activo migrado recibe un nuevo UUID único del sistema. El código interno de Fracttal se mapea al campo "código interno" del nuevo sistema o se almacena en notas de migración si hay conflicto.
- Los activos dados de baja en Fracttal se importan como "Dado de baja" en el nuevo sistema.
- El reporte de migración indica: activos migrados exitosamente (con su nuevo ID), activos con errores (causa), activos con datos incompletos (qué falta), activos sin hospital mapeado (requieren asignación manual).
- El script es idempotente. Usa el código interno o ID de Fracttal como clave de control para no duplicar activos.
