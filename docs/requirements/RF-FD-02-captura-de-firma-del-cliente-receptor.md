---
id: RF-FD-02
issue: 27
titulo: "Captura de firma del cliente/receptor"
tipo: functional
prioridad: must-have
modulo: firma-digital
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: firma-digital']
---

# RF-FD-02 - Captura de firma del cliente/receptor

### RF-FD-02: Captura de firma del cliente/receptor
**Prioridad:** M

**Descripción:**
Al finalizar la visita en el hospital, el técnico puede ofrecer el dispositivo al representante del hospital para que firme como receptor del servicio. Esta firma es opcional pero su ausencia queda documentada.

**Criterios de aceptación:**
- Después de capturar su propia firma, el técnico tiene la opción de "Solicitar firma del receptor" (botón opcional).
- Si se procede: el técnico ingresa el nombre completo y cargo del receptor (campos de texto obligatorios antes de mostrar el canvas) y el receptor firma en el canvas.
- Los datos almacenados son: trazo de firma del receptor (PNG), nombre del receptor (ingresado por el técnico), cargo del receptor, fecha y hora UTC, ID de la OT.
- Si el técnico no solicita la firma del receptor, se muestra un campo "Motivo de no firma del receptor" (texto libre, ejemplos sugeridos: "Cliente no disponible", "Revisión sin intervención física", "Diagnóstico previo sin ejecución") que es obligatorio completar para documentar la razón.
- La firma del receptor y la firma del técnico se muestran en secciones separadas del PDF del reporte.
