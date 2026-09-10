---
id: RF-PDF-01
issue: 29
titulo: "Generación automática del reporte de servicio"
tipo: functional
prioridad: must-have
modulo: pdf
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: pdf', 'needs-fracttal-review']
---

# RF-PDF-01 - Generación automática del reporte de servicio

### RF-PDF-01: Generación automática del reporte de servicio
**Prioridad:** M

**Descripción:**
Al completar una OT, el sistema genera automáticamente el PDF del acta/reporte de servicio respetando los formatos que la empresa ya usa con sus clientes hospitalarios.

**Criterios de aceptación:**
- La generación del PDF inicia automáticamente al cambiar el estado de la OT a "Completada". Se completa en background (Celery) en ≤ 30 segundos para OTs con hasta 20 fotos.
- **Contenido del PDF:**
  - Encabezado: logo de la empresa, nombre de la empresa, datos de contacto, número de OT, tipo de OT, fecha de emisión del documento.
  - Sección de activo: nombre, código interno, número de serie, hospital, área/ubicación, tipo de gas, número de placa INVIMA si aplica.
  - Sección de la intervención: fecha de creación de la OT, fecha de inicio real, fecha de cierre, técnico ejecutor, descripción del trabajo realizado.
  - Checklist completado: todas las secciones y campos con sus respuestas. Valores fuera de rango resaltados visualmente con su observación explicativa.
  - Galería de evidencia: fotos con metadata (coordenadas GPS, timestamp) incrustadas en el PDF con resolución legible. Las fotos de campos específicos del checklist aparecen junto al campo correspondiente.
  - Firma del técnico: imagen del trazo, nombre, cargo, fecha y hora de firma.
  - Firma del receptor/cliente: imagen del trazo, nombre, cargo si fue capturada; o motivo de no firma.
  - Materiales/repuestos utilizados: tabla con nombre, cantidad, y unidad.
  - Observaciones del técnico.
  - Pie de página: número de versión del sistema, hash de integridad del documento, nota legal de firma electrónica.
- El PDF se almacena en S3 vinculado permanentemente a la OT. No se puede eliminar ni sobrescribir.
- El formato del PDF debe respetar los templates actuales de la empresa. **Antes de implementar el generador, se realizará una sesión de trabajo con el cliente para revisar los formatos existentes y mapear exactamente los campos.**
