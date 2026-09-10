---
id: RF-PM-01
issue: 16
titulo: "Creación de plan de mantenimiento"
tipo: functional
prioridad: must-have
modulo: planes-pm
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: planes-pm']
---

# RF-PM-01 - Creación de plan de mantenimiento

### RF-PM-01: Creación de plan de mantenimiento
**Prioridad:** M

**Descripción:**
El `ADMIN` crea planes de mantenimiento que definen qué se hace, en qué activos, con qué periodicidad, y con qué checklist. Un plan activo genera OTs automáticamente de forma continua.

**Criterios de aceptación:**
- **Campos obligatorios del plan:** nombre del plan, alcance de aplicación (uno de: todos los activos de un tipo de activo / activos de un hospital específico / un activo individual), checklist a ejecutar (selección del catálogo), frecuencia de ejecución (opciones: diaria / semanal / quincenal / mensual / bimensual / trimestral / semestral / anual), fecha de inicio del plan.
- **Campos opcionales:** descripción del plan, técnico asignado por defecto (se puede dejar sin asignar para que el ADMIN asigne manualmente cada OT generada), tiempo estimado de ejecución en horas, materiales/repuestos recomendados (preselección del catálogo de inventario), buffer de anticipación en días para generar la OT antes de la fecha de ejecución (por defecto 3 días, configurable entre 1 y 14).
- Al guardar el plan, el sistema calcula y muestra las próximas 5 fechas de ejecución para validación visual del ADMIN antes de confirmar.
- Un plan puede estar en estado: **Activo** (genera OTs automáticamente) o **Pausado** (no genera OTs; las OTs ya generadas y pendientes no se cancelan automáticamente, requiere acción manual).
- El nombre del plan debe ser único en el sistema.
