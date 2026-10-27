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

---

---

**Metadatos de importacion**
- Repositorio destino: `sdeossag/TodoGas`
- Modulo: `MI - Migración de Datos desde Fracttal`
- Prioridad: `M`
- Fuente: `CMMS_Fase1_Requisitos_Funcionales.md`

**Implementación (revisión del 2026-10-27):**
- [x] Procesar la exportación de Fracttal — Se importan las exportaciones de ubicaciones y equipos; el hospital sale del primer nivel de la ruta (no hay archivo de clientes).
- [ ] Importar NIT, ciudad, dirección, correo, teléfono — El hospital se crea solo con nombre y código; el resto se completa a mano porque la exportación no lo trae.
- [x] Hospitales quedan activos — is_active=True.
- [x] No migrar cuentas CLI — No se crean usuarios.
- [x] Reporte de resultados: creados, con errores, incompletos — Vista previa con resumen y errores/avisos por fila antes de aplicar.
- [x] Idempotente por NIT o nombre exacto — Reconoce por nombre sin tildes ni mayúsculas.

Commits: 8fcd0b1, 63baf7a
Archivos: `backend/apps/assets/importacion_fracttal.py`, `backend/apps/assets/views_importacion.py`, `frontend/src/pages/assets/ImportFracttalPage.jsx`
