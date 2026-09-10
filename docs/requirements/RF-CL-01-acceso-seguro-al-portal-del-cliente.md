---
id: RF-CL-01
issue: 49
titulo: "Acceso seguro al portal del cliente"
tipo: functional
prioridad: must-have
modulo: portal-cliente
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: portal-cliente']
---

# RF-CL-01 - Acceso seguro al portal del cliente

### RF-CL-01: Acceso seguro al portal del cliente
**Prioridad:** M

**Descripción:**
El cliente (representante del hospital) accede al portal web con credenciales habilitadas por el ADMIN. Su visibilidad está restringida estrictamente a los datos de su propio hospital.

**Criterios de aceptación:**
- El cliente accede únicamente vía web (no app Android).
- El `ADMIN` crea la cuenta del `CLI` asociada obligatoriamente a un hospital del catálogo. Un CLI solo puede estar asociado a un hospital.
- Al iniciar sesión, el `CLI` ve únicamente los datos de su hospital. Cualquier intento de acceder a recursos de otro hospital (vía URL manipulada o petición API) retorna HTTP 403, no 404 (para no revelar la existencia de otros recursos).
- La sesión del `CLI` expira tras 8 horas de inactividad.
- La interfaz del portal del cliente es diferente visualmente al dashboard del ADMIN/TEC (más simple, centrada en consulta y descarga, sin menús de administración).
- El portal del cliente puede ser accedido desde dispositivo móvil vía navegador (diseño responsive).
