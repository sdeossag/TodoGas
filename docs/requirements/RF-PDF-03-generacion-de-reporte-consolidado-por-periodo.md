---
id: RF-PDF-03
issue: 31
titulo: "Generación de reporte consolidado por período"
tipo: functional
prioridad: should-have
modulo: pdf
estado: OPEN
etiquetas: ['priority: should-have', 'type: functional', 'mod: pdf']
---

# RF-PDF-03 - Generación de reporte consolidado por período

### RF-PDF-03: Generación de reporte consolidado por período
**Prioridad:** S

**Descripción:**
El `ADMIN` puede generar reportes consolidados en PDF para un hospital específico o para todos, filtrando por período de tiempo.

**Criterios de aceptación:**
- El `ADMIN` selecciona: hospital (o "todos"), rango de fechas, tipo de OT (o todos los tipos), y solicita el reporte consolidado.
- El reporte consolidado contiene: resumen ejecutivo (total de OTs por tipo, % de completadas, activos intervenidos), tabla de OTs del período (número, tipo, activo, técnico, fecha, estado, referencia al PDF individual), y gráfico de cumplimiento si se filtra por un solo hospital.
- La generación tarda máx. 60 segundos para períodos de hasta 12 meses con el universo de 3,940 activos.
- El consolidado puede descargarse directamente o enviarse por correo al destinatario que el ADMIN indique.

---

## MÓDULO TR — Trazabilidad e Historial Inmutable
