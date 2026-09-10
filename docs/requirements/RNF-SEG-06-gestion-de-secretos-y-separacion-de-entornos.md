---
id: RNF-SEG-06
issue: 71
titulo: "Gestión de secretos y separación de entornos"
tipo: non-functional
prioridad: must-have
modulo: seguridad
estado: CLOSED
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: seguridad']
---

# RNF-SEG-06 - Gestión de secretos y separación de entornos

### RNF-SEG-06: Gestión de secretos y separación de entornos
**Prioridad:** M

**Descripción:**
Los secretos del sistema se gestionan de forma centralizada y nunca se exponen en el código fuente. Los entornos de desarrollo, staging y producción están completamente separados.

**Criterios de aceptación:**
- El repositorio de GitHub no contiene ningún secreto, credencial, ni clave de API en ningún archivo ni en el historial de commits. Se usa **git-secrets** o equivalente para prevenir commits accidentales de secretos.
- Existen tres entornos completamente separados con sus propias credenciales y bases de datos: **development** (local), **staging** (AWS, para pruebas), **production** (AWS).
- La base de datos de producción no es accesible desde entornos de desarrollo ni staging. El acceso directo a la DB de producción requiere VPN + credenciales con MFA.
- Los secretos de producción solo son conocidos por el servidor de producción (vía Parameter Store/Secrets Manager) y por máximo 2 personas del equipo con acceso a la cuenta AWS de producción.

---

## RNF-ESC — Escalabilidad
