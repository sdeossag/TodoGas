---
id: RF-US-04
issue: 38
titulo: "Onboarding y recuperación de acceso"
tipo: functional
prioridad: must-have
modulo: usuarios-roles
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: usuarios-roles']
---

# RF-US-04 - Onboarding y recuperación de acceso

### RF-US-04: Onboarding y recuperación de acceso
**Prioridad:** M

**Descripción:**
Flujos seguros para el primer acceso de un usuario y para la recuperación de contraseña olvidada.

**Criterios de aceptación:**
- Al primer login con contraseña temporal, el sistema fuerza el cambio de contraseña antes de acceder al sistema. No puede omitirse.
- El flujo de recuperación de contraseña ("olvidé mi contraseña") envía un enlace único al correo registrado. El enlace expira en 1 hora y es de un solo uso.
- Si el correo no está registrado en el sistema, la pantalla de recuperación muestra el mismo mensaje de éxito (para no revelar si un correo existe en el sistema o no).
- El `ADMIN` puede forzar el restablecimiento de contraseña de cualquier usuario desde la interfaz de administración.

---

## MÓDULO BI — Dashboard y Reportes de Gestión
