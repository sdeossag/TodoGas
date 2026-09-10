---
id: RF-US-02
issue: 36
titulo: "Matriz de permisos por rol"
tipo: functional
prioridad: must-have
modulo: usuarios-roles
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: usuarios-roles', 'needs-fracttal-review']
---

# RF-US-02 - Matriz de permisos por rol

### RF-US-02: Matriz de permisos por rol
**Prioridad:** M

**Descripción:**
Los permisos del sistema están definidos por rol sin posibilidad de personalización individual. La matriz cubre todas las acciones sobre todas las entidades del sistema.

**Criterios de aceptación:**

**Rol ADMIN — Acceso total:**
- Crear, editar, dar de baja activos y gestionar toda la jerarquía de activos.
- Crear, asignar, cancelar OTs correctivas y predictivas. Ver todas las OTs.
- Completar OTs (transición En Revisión → Completada).
- Crear, editar, pausar planes de mantenimiento.
- Crear, editar plantillas de checklist.
- Crear, editar, desactivar usuarios de cualquier rol.
- Acceder al log de auditoría completo y exportarlo.
- Generar y enviar cualquier reporte.
- Gestionar inventario (entradas, ajustes manuales).
- Configurar parámetros del sistema (buffer de generación de OTs, umbral de sobrecarga, correos por hospital, etc.).

**Rol SUP — Gestión operativa:**
- Ver todas las OTs y activos (sin restricción de hospital o técnico).
- Completar OTs (transición En Revisión → Completada) y devolver OTs a revisión con comentarios.
- Editar datos técnicos de activos (no puede crear, dar de baja, ni mover activos en la jerarquía).
- Ver (no editar) planes de mantenimiento y plantillas de checklist.
- Ver (no editar) usuarios.
- Ver el log de auditoría, no puede exportarlo.
- No puede gestionar inventario ni crear OTs nuevas.

> ⚠️ Pendiente de validar: confirmar si el rol SUP existe en Fracttal o si debe definirse completamente nuevo para este sistema.

**Rol TEC — Ejecución en campo:**
- Ver únicamente las OTs asignadas a él (todas las demás son invisibles a nivel de API).
- Ejecutar OTs: cambiar a "En Progreso", completar checklist, añadir fotos, firmar, cambiar a "En Revisión".
- Registrar repuestos usados en sus OTs (genera salidas de inventario).
- Ver la ficha técnica (solo lectura) de activos vinculados a sus OTs.
- No puede crear OTs, planes, checklists, ni gestionar usuarios o inventario.

**Rol CLI — Portal de cliente (solo lectura):**
- Ver únicamente los activos de su hospital asignado. El API no retorna activos de otros hospitales bajo ninguna circunstancia.
- Ver las OTs completadas de sus activos (no puede ver OTs en estados intermedios).
- Descargar PDFs de reportes de sus OTs.
- No puede crear, editar, ni eliminar ningún tipo de entidad.
- Acceso solo vía web (no app Android).
