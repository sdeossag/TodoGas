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

---

---

**Metadatos de importacion**
- Tipo: `Requisito no funcional`
- Fase: `2`
- Repositorio destino: `sdeossag/TodoGas`
- Categoria: `USA - Usabilidad en Campo`
- Prioridad: `M`
- Fuente: `CMMS Gases Medicinales - Fase 2: Requisitos No Funcionales`

**Implementación (revisión del 2026-10-27):**
- [ ] Fuente mínima de 16 px — Hay textos text-sm (14 px), incluido el banner offline
- [ ] Área de toque de 48 px y botones primarios de 56 px — Pocas clases de altura mínima; sin revisión sistemática
- [ ] Contraste 4,5:1 — No verificado
- [x] Tema claro por defecto — No hay modo oscuro
- [x] Banner offline visible — OfflineBanner en la parte superior
- [x] Sin gestos precisos para acciones críticas — Botones explícitos y confirmación
- [ ] Máximo 3 toques a la acción común — No medido

Commits: 042cab5
Archivos: `frontend/src/components/ui/OfflineBanner.jsx`, `frontend/tailwind.config.js`
