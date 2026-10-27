---
id: RNF-USA-03
issue: 76
titulo: "Flujos optimizados para rapidez de uso"
tipo: non-functional
prioridad: should-have
modulo: usabilidad
estado: OPEN
etiquetas: ['priority: should-have', 'type: non-functional', 'mod: usabilidad']
---

# RNF-USA-03 - Flujos optimizados para rapidez de uso

### RNF-USA-03: Flujos optimizados para rapidez de uso
**Prioridad:** S

**Descripción:**
Los flujos más repetidos por los técnicos (abrir OT, ejecutar checklist, capturar foto, firmar) están optimizados para completarse con el menor número de pasos posible.

**Criterios de aceptación:**
- El flujo completo de "abrir OT → iniciar → completar checklist simple (10 campos) → añadir 2 fotos → firmar → enviar a revisión" debe poder completarse en **menos de 5 minutos** por un técnico familiarizado con la app (excluyendo el tiempo que tarda la visita técnica en sí).
- La app recuerda el último estado de trabajo del técnico al abrirla: si tenía una OT en progreso cuando cerró la app, esa OT aparece destacada al inicio.
- Los campos del checklist que tienen valor por defecto o que son del tipo "Sí/No" tienen los botones de respuesta inmediatamente visibles sin necesidad de abrir un dropdown.
- La cámara para capturar fotos se abre directamente desde la OT con un solo toque, sin pasos intermedios.
- Todas las acciones destructivas o irreversibles (cancelar OT, borrar foto antes de confirmar) tienen un paso de **confirmación explícita** con descripción de las consecuencias.

---

---

**Metadatos de importacion**
- Tipo: `Requisito no funcional`
- Fase: `2`
- Repositorio destino: `sdeossag/TodoGas`
- Categoria: `USA - Usabilidad en Campo`
- Prioridad: `S`
- Fuente: `CMMS Gases Medicinales - Fase 2: Requisitos No Funcionales`

**Implementación (revisión del 2026-10-27):**
- [ ] Flujo completo en menos de 5 minutos — No medido con usuarios
- [ ] Recuerda la OT en progreso al abrir la app — No se encontró una OT destacada al abrir
- [x] Sí/No con botones visibles — Respuesta Sí/No/N/A con botones
- [x] Cámara desde la OT con un toque — Captura con cámara nativa
- [x] Confirmación en acciones destructivas — Diálogos de confirmación en baja de activos y transiciones

Commits: 334d516, b065c1d
Archivos: `frontend/src/components/evidence/PhotoCapture.jsx`, `frontend/src/components/workOrders/TransitionButton.jsx`
