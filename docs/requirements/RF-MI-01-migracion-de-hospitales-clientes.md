---
id: RF-MI-01
issue: 52
titulo: "Migración de hospitales (clientes)"
tipo: functional
prioridad: must-have
modulo: migracion
estado: OPEN
etiquetas: ['priority: must-have', 'type: functional', 'mod: migracion', 'needs-fracttal-review']
---

# RF-MI-01 - Migración de hospitales (clientes)

### RF-MI-01: Migración de hospitales (clientes)
**Prioridad:** M

**Descripción:**
El catálogo de hospitales/clientes activos en Fracttal se importa al nuevo sistema como paso previo a la migración de activos.

**Criterios de aceptación:**
- La migración procesa el archivo de exportación de clientes de Fracttal (formato a definir según lo que permita la exportación de Fracttal con rol admin).
- Por cada hospital se importan: nombre, NIT/RUT si está disponible, ciudad, dirección, correo de contacto, teléfono. Los campos no disponibles en Fracttal quedan vacíos para completar manualmente.
- Los hospitales migrados quedan en estado "activo" por defecto.
- Las cuentas de acceso (`CLI`) de los hospitales **no se migran** desde Fracttal; el `ADMIN` las crea manualmente en el nuevo sistema con correos validados.
- El script genera un reporte de resultados: hospitales creados exitosamente, hospitales con errores y su causa, hospitales con datos incompletos. El `ADMIN` valida este reporte antes de avanzar a la migración de activos.
- El script es **idempotente:** puede ejecutarse múltiples veces sin duplicar registros. Usa el NIT o el nombre exacto como clave de identificación.
