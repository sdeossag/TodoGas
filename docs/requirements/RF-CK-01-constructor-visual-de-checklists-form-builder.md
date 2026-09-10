---
id: RF-CK-01
issue: 20
titulo: "Constructor visual de checklists (form builder)"
tipo: functional
prioridad: must-have
modulo: checklists
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: checklists']
---

# RF-CK-01 - Constructor visual de checklists (form builder)

### RF-CK-01: Constructor visual de checklists (form builder)
**Prioridad:** M

**Descripción:**
El `ADMIN` puede crear y editar plantillas de checklist desde una interfaz visual sin necesidad de código. El constructor soporta múltiples tipos de campo y agrupación por secciones.

**Criterios de aceptación:**
- El constructor permite: añadir campos de múltiples tipos, reordenar campos con drag & drop, eliminar campos, y agrupar campos en secciones con títulos.
- **Tipos de campo disponibles:**
  - Texto corto (máx. 255 caracteres)
  - Texto largo (máx. 1,000 caracteres)
  - Número (con unidad de medida configurable: PSI, bar, °C, %, etc.)
  - Selección única (radio button con lista de opciones definida por el ADMIN)
  - Selección múltiple (checkbox con lista de opciones definida)
  - Sí / No (boolean)
  - Fecha
  - Rango numérico (valor mínimo y máximo aceptable configurables; si el técnico ingresa fuera del rango, el campo se marca en rojo y se activa un campo de "Observación obligatoria" para que el técnico documente la anomalía)
  - Foto requerida (obliga al técnico a capturar una foto vinculada a ese campo específico)
  - Firma (dispara el flujo de captura de firma digital)
- Cada campo puede marcarse como **Obligatorio** u **Opcional**. Los campos obligatorios no pueden omitirse para completar la OT.
- El constructor permite agrupar campos en secciones con título (ej: "Inspección visual", "Pruebas de presión", "Lectura de manómetros").
- Existe una previsualización del checklist tal como lo verá el técnico en la app Android antes de guardar.
- El nombre del checklist debe ser único en el sistema.
