---
id: RF-OT-07
issue: 14
titulo: "Detalle completo de OT completada"
tipo: functional
prioridad: must-have
modulo: ordenes-trabajo
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: ordenes-trabajo']
---

# RF-OT-07 - Detalle completo de OT completada

### RF-OT-07: Detalle completo de OT completada
**Prioridad:** M

**Descripción:**
Una OT completada presenta toda la información recopilada durante su ejecución en un formato organizado y de solo lectura, consultable por todos los roles con los permisos correspondientes.

**Criterios de aceptación:**
- El detalle muestra: encabezado con número, tipo, activo, hospital, prioridad; sección de fechas (creación, inicio real, cierre, fecha límite); checklist completado con todas las respuestas incluyendo los valores fuera de rango (resaltados en rojo) y sus observaciones obligatorias; galería de fotos con metadata (coordenadas GPS, timestamp, técnico); firma del técnico (imagen); firma del cliente si fue capturada (imagen + nombre + cargo); observaciones del técnico; repuestos utilizados con cantidades; historial de cambios de estado de la OT; enlace de descarga del PDF.
- Toda la información es de solo lectura una vez la OT está en "Completada". No hay botones de edición visibles.
- El detalle es accesible desde la web para `ADMIN`, `SUP`, y `CLI` (con restricción de visibilidad). Para el `TEC`, es accesible desde la app solo para sus OTs propias completadas.
