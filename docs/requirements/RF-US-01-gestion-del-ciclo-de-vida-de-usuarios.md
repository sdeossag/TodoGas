---
id: RF-US-01
issue: 35
titulo: "Gestión del ciclo de vida de usuarios"
tipo: functional
prioridad: must-have
modulo: usuarios-roles
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: usuarios-roles']
---

# RF-US-01 - Gestión del ciclo de vida de usuarios

### RF-US-01: Gestión del ciclo de vida de usuarios
**Prioridad:** M

**Descripción:**
Solo el `ADMIN` puede gestionar los usuarios del sistema: crear, editar, activar, desactivar. No existe eliminación física de usuarios.

**Criterios de aceptación:**
- **Al crear un usuario, campos obligatorios:** nombre completo, correo electrónico (único en el sistema, usado como username), rol (ADMIN / SUP / TEC / CLI), estado inicial (activo por defecto).
- **Campos adicionales por rol:** para `TEC`: número de carnet/empleado, teléfono de contacto. Para `CLI`: hospital al que pertenece (selección obligatoria del catálogo de hospitales; un CLI solo puede estar asociado a un hospital).
- **Campos opcionales para todos:** foto de perfil.
- Al crear el usuario, el sistema genera una contraseña temporal segura (16 caracteres aleatorios) y envía un correo al nuevo usuario con: bienvenida, URL de acceso al sistema, contraseña temporal, e instrucciones para cambiar la contraseña en el primer login. El enlace del correo de activación expira a las 48 horas.
- El `ADMIN` puede desactivar un usuario (impide el login inmediatamente). Las sesiones activas del usuario desactivado se invalidan en la siguiente petición al servidor.
- Un usuario desactivado conserva todo su historial en el sistema (OTs ejecutadas, log de acciones, etc.).
- No existe eliminación de usuarios bajo ninguna circunstancia.
- El `ADMIN` puede restablecer la contraseña de cualquier usuario (genera nueva contraseña temporal y envía correo).
