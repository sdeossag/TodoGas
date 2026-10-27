---
id: REV-11
issue: 107
titulo: "Configurar qué campos aparecen en el acta PDF"
tipo: functional
prioridad: should-have
modulo: pdf
estado: CLOSED
etiquetas: ['priority: should-have', 'type: functional', 'mod: pdf']
---

# REV-11 - Configurar qué campos aparecen en el acta PDF

### REV-11: Configurar qué campos aparecen en el acta PDF
**Prioridad:** S

**Descripción:**
El cliente no quiere editar el contenido del acta sino elegir qué se muestra, como regla general y no por PDF. Pidió quitar fecha de finalización, técnico, bloque de fotos del checklist y firma duplicada, y añadir el grupo del campo y el tipo de intervención.

**Criterios de aceptación:**
- [x] Configuración de la plantilla a nivel de organización
- [x] Se pueden apagar campos como ejecutor, fechas y fotos
- [x] El acta muestra el tipo de intervención y las secciones por grupo
- [x] Lo que prueba el servicio no se puede apagar

**Implementación:**
Catálogo de opciones del acta con interruptores (8349191), hora real y ejecutor (1ba2e09) y acta simplificada con un cuadro por activo (6e45d14). Archivos: backend/apps/reports/options.py, generator.py y la plantilla service_report.html.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `pdf`
- Prioridad: `S`
- Fuente: `Revisión con el cliente (2026-09-10)`
