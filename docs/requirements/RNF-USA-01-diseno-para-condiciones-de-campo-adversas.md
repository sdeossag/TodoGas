---
id: RNF-USA-01
issue: 74
titulo: "Diseño para condiciones de campo adversas"
tipo: non-functional
prioridad: must-have
modulo: usabilidad
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: usabilidad']
---

# RNF-USA-01 - Diseño para condiciones de campo adversas

### RNF-USA-01: Diseño para condiciones de campo adversas
**Prioridad:** M

**Descripción:**
La app Android está diseñada para ser usada por técnicos que trabajan en condiciones físicas adversas: guantes, luz solar directa, prisa, suciedad en el dispositivo, y conectividad intermitente o nula.

**Criterios de aceptación:**
- **Tamaño de fuente mínimo:** 16sp (scale-independent pixels) en todos los textos de la interfaz de la app.
- **Área de toque mínima:** 48dp × 48dp para todos los elementos interactivos (botones, campos, íconos). Los botones primarios de acción (Iniciar OT, Enviar a Revisión, Confirmar Firma) tienen altura mínima de 56dp.
- **Contraste de color:** ratio mínimo de 4.5:1 entre texto y fondo (WCAG AA) para legibilidad en exteriores con luz solar directa.
- **Modo de pantalla brillante:** la app no fuerza un tema oscuro que sería difícil de leer en exteriores. El tema por defecto es claro con colores de alto contraste.
- **Compatibilidad con guantes:** los elementos de toque no requieren gestos precisos (no hay swipe-to-delete ni doble tap para acciones críticas). Las acciones críticas tienen botones explícitos y grandes.
- **Indicador de modo offline prominente:** cuando la app está sin conexión, un banner visible en la parte superior de la pantalla muestra "● Sin conexión — Modo offline activo" en color naranja o amarillo. No es sutil ni pequeño.
- Los flujos de la app no requieren más de **3 toques** para llegar a la acción más común de cada pantalla (ver OT asignada, iniciar OT, añadir foto).
