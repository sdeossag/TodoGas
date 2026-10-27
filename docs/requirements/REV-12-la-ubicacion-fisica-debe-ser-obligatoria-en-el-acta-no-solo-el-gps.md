---
id: REV-12
issue: 108
titulo: "La ubicación física debe ser obligatoria en el acta, no solo el GPS"
tipo: functional
prioridad: must-have
modulo: pdf
estado: OPEN
etiquetas: ['priority: must-have', 'type: functional', 'mod: pdf']
---

# REV-12 - La ubicación física debe ser obligatoria en el acta, no solo el GPS

### REV-12: La ubicación física debe ser obligatoria en el acta, no solo el GPS
**Prioridad:** M

**Descripción:**
El GPS no distingue equipos dentro de un mismo edificio y varios activos comparten nombre. Se pidió mostrar la ruta completa de ubicación en el acta y que sea siempre obligatoria.

**Criterios de aceptación:**
- [x] El acta muestra la ruta completa de ubicación del activo
- [x] La ubicación de la visita viaja con la OT
- [ ] La ubicación no se puede apagar en la configuración del acta

**Implementación:**
Ruta de ubicación con dirección y mapa en el acta (5ed8863, 8caf0ef), regida por las opciones del acta (8349191). Falta volverla obligatoria. Archivos: backend/apps/reports/options.py, generator.py.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `pdf`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-09-10)`
