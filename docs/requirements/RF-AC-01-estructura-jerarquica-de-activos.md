---
id: RF-AC-01
issue: 1
titulo: "Estructura jerárquica de activos"
tipo: functional
prioridad: must-have
modulo: activos
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: activos', 'needs-fracttal-review']
---

# RF-AC-01 - Estructura jerárquica de activos

### RF-AC-01: Estructura jerárquica de activos
**Prioridad:** M

**Descripción:**
El sistema organiza los activos en una jerarquía de hasta 5 niveles: **Hospital (Cliente) > Sede/Área > Sistema > Equipo > Componente**. Cada nodo puede tener nodos hijos. Un activo puede existir en cualquier nivel de la jerarquía. La jerarquía es la unidad organizacional principal de todo el sistema.

> ⚠️ Pendiente de validar: confirmar los niveles exactos de jerarquía tal como están definidos en Fracttal antes de implementar el modelo de datos.

**Criterios de aceptación:**
- El sistema soporta crear, editar y mover nodos en cualquiera de los 5 niveles.
- La jerarquía se visualiza como árbol colapsable/expandible en la interfaz web, con conteo de hijos por nodo.
- Al seleccionar un nodo, el sistema muestra todos sus hijos directos e indirectos (árbol completo del subárbol).
- No se puede eliminar ni dar de baja un nodo que tenga hijos activos; el sistema bloquea la acción con un mensaje explicativo que lista los hijos afectados.
- Cada nivel tiene campos diferenciados: el nivel "Hospital" incluye NIT, dirección, ciudad, correo de contacto; el nivel "Equipo" incluye número de serie, modelo, marca, y datos técnicos específicos.
- Un activo puede ser reasignado a otro padre mediante una operación de "mover", que registra automáticamente el movimiento en el log de trazabilidad (quién, cuándo, de dónde, hacia dónde).
- La búsqueda de activos respeta la jerarquía: buscar en un nodo padre retorna resultados de todos sus descendientes.
