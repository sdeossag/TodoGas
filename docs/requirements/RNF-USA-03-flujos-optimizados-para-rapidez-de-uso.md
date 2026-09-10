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
