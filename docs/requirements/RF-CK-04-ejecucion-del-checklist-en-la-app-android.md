---
id: RF-CK-04
issue: 23
titulo: "Ejecución del checklist en la app Android"
tipo: functional
prioridad: must-have
modulo: checklists
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: checklists']
---

# RF-CK-04 - Ejecución del checklist en la app Android

### RF-CK-04: Ejecución del checklist en la app Android
**Prioridad:** M

**Descripción:**
La ejecución del checklist desde la app está optimizada para campo: fuente grande, áreas de toque amplias, guardado automático, y retroalimentación inmediata sobre valores fuera de rango.

**Criterios de aceptación:**
- Los campos del checklist se organizan por secciones con pestañas o scroll; el técnico puede navegar entre secciones con botones de "Anterior" y "Siguiente" o scroll libre.
- Fuente mínima de 16px en todos los campos. Áreas de toque mínimas de 48px de alto.
- Los campos tipo "Foto requerida" abren directamente la cámara del dispositivo al tocarlos; la foto tomada queda vinculada explícitamente a ese campo y se muestra como miniatura junto al campo completado.
- Los campos tipo "Rango numérico": al salir del campo (perder foco) el sistema evalúa el valor inmediatamente; si está fuera del rango, el campo se colorea en rojo y aparece un área de texto de "Observación obligatoria" directamente debajo que el técnico debe completar antes de avanzar.
- El progreso del checklist se guarda automáticamente cada 30 segundos en almacenamiento local del dispositivo (SQLite). Si la app se cierra y se vuelve a abrir, el técnico retoma desde donde lo dejó.
- Un indicador de progreso (ej: "Sección 2 de 4 — 7/12 campos completados") es siempre visible.
- El botón "Finalizar Checklist" solo se habilita cuando todos los campos obligatorios están completos y sin errores de rango sin observación.

---

## MÓDULO EV — Captura de Evidencia Fotográfica
