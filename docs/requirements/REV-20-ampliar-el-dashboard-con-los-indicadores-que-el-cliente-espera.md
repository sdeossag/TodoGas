---
id: REV-20
issue: 115
titulo: "Ampliar el dashboard con los indicadores que el cliente espera"
tipo: functional
prioridad: could-have
modulo: dashboard-bi
estado: OPEN
etiquetas: ['priority: could-have', 'type: functional', 'mod: dashboard-bi']
---

# REV-20 - Ampliar el dashboard con los indicadores que el cliente espera

### REV-20: Ampliar el dashboard con los indicadores que el cliente espera
**Prioridad:** C

**Descripción:**
El cliente comparó el dashboard con otro sistema que tiene más indicadores y no entendió de dónde salía la métrica de cumplimiento. Se necesita revisar qué indicadores le sirven, documentar cómo se calcula cada uno y quitar el costo si no se usa.

**Criterios de aceptación:**
- [x] Contratos por atender en el tablero
- [x] Indicador de costo retirado de la OT
- [ ] Cada indicador explica en la interfaz cómo se calcula
- [ ] Indicadores confirmados con el cliente

**Implementación:**
Tarjetas de atención con contratos, hallazgos abiertos y paneles de planeación (5ed8863); cumplimiento en el portal del hospital (fa7c469). Archivos: frontend/src/components/dashboard, backend/apps/work_orders/dashboard.py.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `dashboard-bi`
- Prioridad: `C`
- Fuente: `Revisión con el cliente (2026-09-10)`
