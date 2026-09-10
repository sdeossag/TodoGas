---
id: RNF-SEG-03
issue: 68
titulo: "Control de acceso y autorización a nivel de datos"
tipo: non-functional
prioridad: must-have
modulo: seguridad
estado: CLOSED
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: seguridad']
---

# RNF-SEG-03 - Control de acceso y autorización a nivel de datos

### RNF-SEG-03: Control de acceso y autorización a nivel de datos
**Prioridad:** M

**Descripción:**
El sistema implementa autorización a nivel de fila (row-level security) en el API para garantizar que ningún usuario pueda acceder a datos que no le pertenecen, incluso manipulando peticiones HTTP directamente.

**Criterios de aceptación:**
- Todos los viewsets y endpoints de Django REST Framework tienen **permisos explícitos definidos** (no dependen del permiso por defecto). El permiso por defecto global es `IsAuthenticated`; los permisos específicos por recurso se definen en cada view.
- Los querysets de todos los endpoints están **filtrados por el contexto del usuario autenticado** antes de retornar datos. Un `CLI` que intente acceder a `/api/activos/?hospital=otro_hospital_id` no recibe datos de ese hospital; el filtro aplica a nivel de queryset independientemente de los parámetros recibidos.
- Los intentos de acceso a recursos de otro usuario o hospital retornan HTTP **403** (no 404) para no revelar la existencia de recursos.
- Se implementan pruebas automatizadas de autorización que verifican que cada endpoint devuelve el código correcto (403 o 200) para cada combinación de rol y recurso. Estas pruebas corren en el pipeline de CI en cada PR.
- El log de auditoría registra todos los intentos de acceso no autorizado (403) con: usuario, endpoint solicitado, timestamp.
