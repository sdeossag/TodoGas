---
id: RF-CL-03
issue: 51
titulo: "Historial de OTs y descarga de reportes"
tipo: functional
prioridad: must-have
modulo: portal-cliente
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: portal-cliente']
---

# RF-CL-03 - Historial de OTs y descarga de reportes

### RF-CL-03: Historial de OTs y descarga de reportes
**Prioridad:** M

**Descripción:**
El cliente puede consultar el historial completo de intervenciones en sus activos y descargar los reportes PDF de cada una.

**Criterios de aceptación:**
- El historial de OTs del `CLI` muestra solo OTs en estado "Completada" de sus activos. Las OTs en otros estados no son visibles.
- Columnas del listado: número de OT, tipo de intervención, nombre del activo, área, fecha de cierre, técnico que la ejecutó.
- Al acceder al detalle de una OT completada, el `CLI` ve: datos del activo, descripción de la intervención, checklist completado con respuestas (sin los metadatos internos del sistema), galería de fotos con fecha y hora de captura (sin coordenadas GPS ni datos internos), firma del técnico, firma del receptor (si fue capturada), observaciones del técnico, repuestos utilizados.
- Cada OT tiene un botón de descarga directa del PDF del reporte.
- El sistema registra en el log de auditoría cada descarga de PDF por un `CLI` (fecha, usuario, documento descargado).
- Los reportes permanecen disponibles para descarga indefinidamente.

---

## MÓDULO MI — Migración de Datos desde Fracttal
