---
id: RNF-REN-03
issue: 61
titulo: "Rendimiento de la app Android en dispositivos de gama media"
tipo: non-functional
prioridad: must-have
modulo: rendimiento
estado: CLOSED
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: rendimiento']
---

# RNF-REN-03 - Rendimiento de la app Android en dispositivos de gama media

### RNF-REN-03: Rendimiento de la app Android en dispositivos de gama media
**Prioridad:** M

**Descripción:**
La app Android (empaquetada con Capacitor) debe ofrecer una experiencia fluida en los dispositivos Android de gama media que usan los técnicos de campo, donde los recursos de CPU y RAM son limitados.

**Criterios de aceptación:**
- **Inicio de la app** (splash a pantalla de login): ≤ 3 segundos en dispositivo con 3 GB de RAM y procesador octa-core de gama media (ej: Snapdragon 6xx o MediaTek Helio G series).
- **Tiempo de apertura de una OT** (desde listado al detalle completo, con datos offline disponibles): ≤ 1.5 segundos.
- **Renderizado del checklist:** los campos de un checklist con hasta 50 ítems se renderizan completamente en ≤ 1 segundo sin jank visible (sin caídas por debajo de 30 fps durante el scroll).
- **Captura de foto:** desde el botón "capturar foto" hasta que la miniatura aparece en la pantalla (incluyendo compresión): ≤ 3 segundos.
- La app no consume más de **200 MB de RAM** durante uso intensivo (ejecución de OT con checklist + galería de fotos activa).
- El consumo de batería durante 4 horas de uso activo en campo (con GPS activo y pantalla encendida) no supera el 40% de batería en un dispositivo con batería de 4,000 mAh. Se mide y documenta antes del release.
