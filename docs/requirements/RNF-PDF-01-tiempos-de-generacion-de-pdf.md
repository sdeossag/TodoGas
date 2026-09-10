---
id: RNF-PDF-01
issue: 86
titulo: "Tiempos de generación de PDF"
tipo: non-functional
prioridad: must-have
modulo: pdf
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: pdf']
---

# RNF-PDF-01 - Tiempos de generación de PDF

### RNF-PDF-01: Tiempos de generación de PDF
**Prioridad:** M

**Descripción:**
La generación de PDFs debe completarse en tiempos que no generen una espera perceptible para el ADMIN ni retrasen el envío automático al cliente.

**Criterios de aceptación:**
- **PDF de reporte de servicio individual** (hasta 20 fotos, 1 checklist de hasta 50 ítems, 2 firmas): se genera en ≤ **30 segundos** mediante tarea Celery en background.
- **PDF de reporte consolidado** (hasta 12 meses de OTs de un hospital): se genera en ≤ **60 segundos**.
- **PDF de etiqueta QR** de activo: se genera en ≤ **5 segundos** (sincrónico, a petición del ADMIN desde la interfaz web).
- Si la generación de un PDF tarda más del tiempo límite definido (timeout de Celery), la tarea se marca como fallida, el ADMIN recibe alerta, y puede reintentar manualmente desde la interfaz.
- Los PDFs generados se almacenan en S3 inmediatamente después de su generación y son accesibles para descarga sin regenerarse (la URL apunta al archivo ya generado, no a un endpoint que lo genera en tiempo real).
