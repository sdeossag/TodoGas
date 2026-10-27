---
id: REV-05
issue: 100
titulo: "Interfaz para gestionar el árbol de ubicaciones dentro de cada hospital"
tipo: functional
prioridad: must-have
modulo: activos
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: activos']
---

# REV-05 - Interfaz para gestionar el árbol de ubicaciones dentro de cada hospital

### REV-05: Interfaz para gestionar el árbol de ubicaciones dentro de cada hospital
**Prioridad:** M

**Descripción:**
El modelo de nodos existía y la API ya lo soportaba, pero faltaba la interfaz para crear, renombrar, mover y desactivar ubicaciones y ubicar activos en ellas. La jerarquía real es institución, bloque, piso, servicio y activo.

**Criterios de aceptación:**
- [x] Crear, renombrar, mover y desactivar nodos desde la interfaz
- [x] Selector de ubicación en el formulario de activo
- [x] Eliminar un nodo con contenido está bloqueado con mensaje claro

**Implementación:**
Editor del árbol de ubicaciones por hospital (a45fa8d) y dirección con punto en el mapa para cada ubicación (8caf0ef). Validación de borrado en backend/apps/assets/views.py.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `activos`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
