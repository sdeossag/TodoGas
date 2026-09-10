---
id: RF-TR-03
issue: 34
titulo: "Integridad e inmutabilidad de OTs completadas"
tipo: functional
prioridad: must-have
modulo: trazabilidad
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: trazabilidad']
---

# RF-TR-03 - Integridad e inmutabilidad de OTs completadas

### RF-TR-03: Integridad e inmutabilidad de OTs completadas
**Prioridad:** M

**Descripción:**
Una OT en estado "Completada" es un registro sellado que no puede ser modificado bajo ninguna circunstancia. El sistema garantiza y puede verificar esta integridad en cualquier momento.

**Criterios de aceptación:**
- Ningún usuario (incluyendo `ADMIN`) puede editar ningún campo de una OT completada: descripción, checklist, fotos, firmas, observaciones, repuestos usados.
- Si se necesita documentar un addendum o corrección posterior a una OT completada, el flujo correcto es crear una nueva OT correctiva que referencie la OT original en su descripción.
- El hash SHA-256 de la OT (calculado sobre todos sus datos en el momento de la transición a "Completada") se almacena en base de datos en un campo de solo-escritura.
- El `ADMIN` puede ejecutar una **verificación de integridad** desde la interfaz que recalcula el hash actual de la OT y lo compara con el hash almacenado; si coinciden, se muestra "Integridad verificada ✓"; si no coinciden (indicaría manipulación directa en base de datos), se muestra una alerta crítica.
- Cualquier intento de modificar una OT completada vía API es rechazado con HTTP 403, y el intento queda registrado en el log de auditoría.

---

## MÓDULO US — Usuarios, Roles y Permisos
