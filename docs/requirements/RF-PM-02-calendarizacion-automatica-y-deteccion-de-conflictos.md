---
id: RF-PM-02
issue: 17
titulo: "Calendarización automática y detección de conflictos"
tipo: functional
prioridad: must-have
modulo: planes-pm
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: planes-pm']
---

# RF-PM-02 - Calendarización automática y detección de conflictos

### RF-PM-02: Calendarización automática y detección de conflictos
**Prioridad:** M

**Descripción:**
El sistema calcula automáticamente las fechas de ejecución, genera OTs con anticipación configurable, y detecta situaciones de sobrecarga de trabajo para los técnicos.

**Criterios de aceptación:**
- La tarea de generación corre diariamente y genera OTs con X días de anticipación según el buffer de cada plan.
- Si la fecha de ejecución calculada cae en sábado o domingo, la OT se genera el viernes anterior con la fecha límite real (fin de semana), o se pospone al lunes siguiente, según una configuración global del sistema (por defecto: posponer al lunes).
- El `ADMIN` puede ver un **calendario mensual interactivo** con todas las OTs preventivas programadas, filtrable por hospital, activo, y técnico.
- **Detección de sobrecarga:** si un técnico tiene más de N OTs asignadas para un mismo día (N configurable por el ADMIN, por defecto 4), el sistema marca ese día como "sobrecargado" en el calendario y envía una alerta al ADMIN para que redistribuya manualmente.
- El calendario permite ver semanas y meses, y al hacer clic en una OT programada abre su detalle.
