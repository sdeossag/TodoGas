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

---

---

**Metadatos de importacion**
- Tipo: `Requisito no funcional`
- Fase: `2`
- Repositorio destino: `sdeossag/TodoGas`
- Categoria: `PDF - Generación de Documentos PDF`
- Prioridad: `M`
- Fuente: `CMMS Gases Medicinales - Fase 2: Requisitos No Funcionales`

**Implementación (revisión del 2026-10-27):**
- [ ] Acta en 30 s por Celery — Se genera por Celery; sin medición ni tiempo máximo
- [ ] Consolidado en 60 s — Sin medir
- [ ] Etiqueta QR en 5 s — Se genera al momento, pero como PNG y no PDF; sin medir
- [ ] Si excede el tiempo: tarea fallida, alerta y reintento manual — No hay time_limit; sí hay registro de fallo y regeneración manual
- [x] PDF guardado en S3 y descargable sin regenerar — GeneratedReport con archivo en S3

Commits: 6c2cef8, 2d98ffb
Archivos: `backend/apps/reports/tasks.py`, `backend/apps/reports/generator.py`, `backend/apps/assets/views.py`
