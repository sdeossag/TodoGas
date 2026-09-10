---
id: RF-FD-01
issue: 26
titulo: "Captura de firma del técnico"
tipo: functional
prioridad: must-have
modulo: firma-digital
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: firma-digital']
---

# RF-FD-01 - Captura de firma del técnico

### RF-FD-01: Captura de firma del técnico
**Prioridad:** M

**Descripción:**
Al cerrar una OT, el técnico captura su firma digital en la pantalla táctil del dispositivo Android. Esta firma queda criptográficamente vinculada a la OT y es parte integral del reporte de servicio.

**Criterios de aceptación:**
- El paso de firma del técnico aparece como el penúltimo paso en el flujo de cierre de OT, después de completar el checklist y antes de enviar a revisión.
- El canvas de firma tiene mínimo 300px de ancho × 150px de alto, con sensibilidad al trazo táctil. El trazo se renderiza en tiempo real en color negro sobre fondo blanco.
- El técnico puede borrar y repetir la firma ilimitadas veces antes de confirmarla.
- Al confirmar la firma, el sistema captura y almacena de forma inmutable: imagen PNG del trazo de firma (300x150px mínimo), nombre completo del firmante (del perfil autenticado en el sistema), rol ("Técnico de campo"), fecha y hora UTC de la confirmación, identificador único de la OT firmada, hash SHA-256 del estado actual del contenido de la OT (checklist + fotos + observaciones + datos de OT) en el momento de firmar.
- Una vez confirmada, la firma no puede modificarse ni eliminarse por ningún rol.
- La imagen de firma se almacena en S3 y se incrusta en el PDF del reporte.
