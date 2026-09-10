---
id: RF-US-03
issue: 37
titulo: "Autenticación segura y gestión de sesiones"
tipo: functional
prioridad: must-have
modulo: usuarios-roles
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: usuarios-roles']
---

# RF-US-03 - Autenticación segura y gestión de sesiones

### RF-US-03: Autenticación segura y gestión de sesiones
**Prioridad:** M

**Descripción:**
El sistema implementa autenticación mediante JWT con políticas de seguridad robustas, bloqueo por intentos fallidos, y gestión de sesiones activas.

**Criterios de aceptación:**
- Autenticación mediante JWT: access token con expiración de 8 horas, refresh token con expiración de 7 días.
- **Política de contraseñas:** mínimo 8 caracteres, al menos 1 mayúscula, al menos 1 número, al menos 1 carácter especial. El sistema rechaza las 5 contraseñas anteriores del usuario al hacer un cambio.
- Después de **5 intentos fallidos consecutivos** de login, la cuenta se bloquea durante 30 minutos. El `ADMIN` puede desbloquear manualmente antes de ese tiempo.
- HTTPS obligatorio en todas las comunicaciones. HTTP es redirigido automáticamente a HTTPS (301).
- Los tokens JWT contienen únicamente: user ID (UUID, no secuencial), rol, y timestamp de expiración. No contienen datos personales ni sensibles.
- El logout invalida el refresh token en el servidor (lista negra de tokens revocados). Un access token válido pero cuyo refresh fue revocado no puede renovarse.
- El usuario puede ver sus sesiones activas (dispositivo, IP, última actividad) y cerrarlas de forma remota individualmente o todas a la vez.
- La sesión del `CLI` expira tras 8 horas de inactividad (sin actividad de API); no puede usar refresh token después de ese tiempo de inactividad.
