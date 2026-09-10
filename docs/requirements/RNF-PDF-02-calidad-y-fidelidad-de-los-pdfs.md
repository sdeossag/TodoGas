---
id: RNF-PDF-02
issue: 87
titulo: "Calidad y fidelidad de los PDFs"
tipo: non-functional
prioridad: must-have
modulo: pdf
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: pdf']
---

# RNF-PDF-02 - Calidad y fidelidad de los PDFs

### RNF-PDF-02: Calidad y fidelidad de los PDFs
**Prioridad:** M

**Descripción:**
Los PDFs generados son de calidad profesional, imprimibles, y cumplen con los estándares visuales que la empresa ya usa con sus clientes hospitalarios.

**Criterios de aceptación:**
- Las fotos incrustadas en el PDF tienen resolución mínima de **150 DPI** para impresión en papel carta (8.5 × 11"). La calidad es legible en impresión sin pixelación visible.
- Las firmas capturadas son nítidas y reconocibles en el PDF en el tamaño en que se imprimen.
- Los PDFs son válidos según el estándar **PDF/A-2b** (archivado de largo plazo), que garantiza que sean abribles en el futuro sin dependencia de software específico.
- El tamaño máximo de un PDF de reporte individual (con 20 fotos) es de **15 MB**. Si se supera, la librería de generación comprime las imágenes adicional.
- Los PDFs son abribles sin contraseña en Adobe Acrobat Reader, Chrome PDF Viewer, y cualquier lector de PDF estándar. No se aplica protección de contraseña ni restricciones de impresión.
- El template de PDF se construye en sesión de trabajo con el ADMIN de la empresa antes de implementar el generador, para mapear exactamente los campos y el formato a respetar.
