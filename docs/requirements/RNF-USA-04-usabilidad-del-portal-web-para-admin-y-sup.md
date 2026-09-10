---
id: RNF-USA-04
issue: 77
titulo: "Usabilidad del portal web para ADMIN y SUP"
tipo: non-functional
prioridad: should-have
modulo: usabilidad
estado: OPEN
etiquetas: ['priority: should-have', 'type: non-functional', 'mod: usabilidad']
---

# RNF-USA-04 - Usabilidad del portal web para ADMIN y SUP

### RNF-USA-04: Usabilidad del portal web para ADMIN y SUP
**Prioridad:** S

**Descripción:**
La interfaz web es usable sin entrenamiento extenso para usuarios con conocimientos básicos de computador. El diseño sigue convenciones estándar de aplicaciones web de gestión.

**Criterios de aceptación:**
- Un nuevo usuario `ADMIN` puede completar las tareas más importantes (crear un activo, crear una OT, asignar un técnico, revisar el dashboard) sin consultar un manual, siguiendo solo los indicadores visuales de la interfaz. Esto se valida con una prueba de usabilidad con al menos 2 usuarios reales antes del lanzamiento.
- Todos los formularios tienen etiquetas claras, mensajes de error específicos al lado del campo que los generó (no mensajes genéricos al inicio del formulario), y guías de formato cuando aplica (ej: "Ej: 2026-01-15" para campos de fecha).
- La interfaz web es **responsive** para ser usable desde una tablet o laptop con pantalla de 10" o mayor. No necesita ser óptima en celular (ese uso es para la app Android).
- Los mensajes del sistema están en **español colombiano** sin anglicismos de interfaz. No aparecen textos en inglés en la UI del usuario final.
- Las acciones con consecuencias importantes (dar de baja un activo, cancelar una OT, eliminar un técnico) tienen un diálogo de confirmación que describe exactamente qué va a pasar.

---

## RNF-COM — Cumplimiento Normativo
